import gdown
import os
import logging
import re
from pymongo import MongoClient


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


drive_folder_link = 'https://drive.google.com/drive/u/1/folders/1q-UsC5f_Kh-j2-HUi6nGL95iDKkTuJwo'
output_folder = './downloaded_files'


def download_files_from_drive(folder_url):
    file_ids = [
        "1qJdfnqShY6oKDaiwXRFzh_8XlUelUNj2",  # Replace with actual file IDs
        "1vtfKG8agockbMbkxmCK2LNSxImnN_F0s"   # Replace with actual file IDs
    ]
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file_id in file_ids:
        try:
            logging.info(f"Downloading file with ID: {file_id}")
            gdown.download(f"https://drive.google.com/uc?export=download&id={file_id}", 
                           output=os.path.join(output_folder, f"{file_id}.txt"), quiet=False)
            logging.info(f"File downloaded successfully: {file_id}")
        except Exception as e:
            logging.error(f"Error downloading file {file_id}: {e}")

download_files_from_drive(drive_folder_link)


mongo_uri = ""

try:
    logging.info("Connecting to MongoDB Atlas...")
    client = MongoClient(mongo_uri)
    db = client['']  
    collection = db['Cases'] 
    logging.info("Connected to MongoDB Atlas successfully.")
except Exception as e:
    logging.error(f"Error connecting to MongoDB: {e}")
    exit()


def process_and_insert_to_mongo():
    for filename in os.listdir(output_folder):
        if filename.endswith('.txt'):
            try:
                logging.info(f"Processing file: {filename}")
                with open(os.path.join(output_folder, filename), 'r', encoding='utf-8') as file:
                    file_content = file.read()

                    if not file_content:
                        logging.warning(f"Skipping empty file: {filename}")
                        continue
                    
                    # Initialize project dictionary
                    project = {
                        "title": "",
                        "short_description": "",
                        "difficulty": "",
                        "safety_precautions": [],
                        "tools_required": [],
                        "materials_required": [],
                        "steps": [],
                        "common_mistakes": [],
                        "expected_outcome": [],
                        "reference_links": []
                    }

                    # Helper function to clean up text and remove extra spaces
                    def clean_text(text):
                        return ' '.join(text.lstrip('-').strip().split())

                    # Extract project title
                    title_match = re.search(r"Project Title:\s*(.*)", file_content)
                    if title_match:
                        project["title"] = clean_text(title_match.group(1))
                    else:
                        logging.warning("Project title not found.")

                    # Extract short description
                    description_match = re.search(r"Short Description:\s*(.*)", file_content)
                    if description_match:
                        project["short_description"] = clean_text(description_match.group(1))
                    else:
                        logging.warning("Short description not found.")

                    # Extract difficulty
                    difficulty_match = re.search(r"Difficulty:\s*(.*)", file_content)
                    if difficulty_match:
                        project["difficulty"] = clean_text(difficulty_match.group(1))
                    else:
                        logging.warning("Difficulty not found.")

                    # Extract safety precautions
                    safety_precautions_match = re.search(r"Safety Precautions:\s*(.*?)(Tools Required:)", file_content, re.DOTALL)
                    if safety_precautions_match:
                        project["safety_precautions"] = [
                            clean_text(line.strip()) for line in safety_precautions_match.group(1).splitlines() if line.strip()]
                    else:
                        logging.warning("No safety precautions section found.")

                    # Extract project-level tools
                    tools_match = re.search(r"Tools Required:\s*(.*?)(?=\n\s*Materials Required:)", file_content, re.DOTALL)
                    if tools_match:
                        project["tools_required"] = [
                            clean_text(line) for line in tools_match.group(1).splitlines() if line.strip()
                        ]
                    else:
                        logging.warning("No tools required section found.")

                    # Extract project-level materials
                    materials_match = re.search(r"Materials Required:\s*(.*?)(?=\n\s*Steps:)", file_content, re.DOTALL)
                    if materials_match:
                        project["materials_required"] = [
                            clean_text(line) for line in materials_match.group(1).splitlines() if line.strip()
                        ]
                    else:
                        logging.warning("No materials required section found.")

                    # Extract tools and materials for each step
                    step_start = re.search(r"Steps:", file_content)
                    if step_start:
                        steps_content = file_content[step_start.end():]
                        step_lines = steps_content.splitlines()
                        step_count = 0
                        current_step = {"description": "", "tools": [], "materials": [], "image": ""}

                        for step_line in step_lines:
                            if step_line.startswith("Step"):
                                
                                if current_step["description"]:  # Check if description is populated
                                    project["steps"].append(current_step)
                                current_step = {
                                    "step_number": step_count + 1,
                                    "description": "",
                                    "tools": [],
                                    "materials": [],
                                    "image": f"/images/step{step_count + 1}.jpg"
                                }
                                step_count += 1
                                
                            if "Description:" in step_line:
                                current_step["description"] += clean_text(step_line.split(":")[1].strip()) + " "
                            elif "Tools:" in step_line:
                                current_step["tools"] = [clean_text(item.strip()) for item in step_line.split(":")[1].split(",")]
                            elif "Materials:" in step_line:
                                current_step["materials"] = [clean_text(item.strip()) for item in step_line.split(":")[1].split(",")]
                            elif current_step and "step_number" in current_step and step_line.strip() \
                                and not step_line.strip().lstrip("- ").startswith("Image:"):
                                # Only append free text to the description of an active step.
                                current_step["description"] += clean_text(step_line.strip()) + " "
                        
                        if current_step["description"]:  
                            project["steps"].append(current_step)

                    else:
                        logging.warning("No steps section found.")

                    
                    mistakes_start = re.search(r"Common Mistakes to Avoid:\s*", file_content)
                    if mistakes_start:
                        mistakes_content = file_content[mistakes_start.end():]
                        mistakes_end = re.search(r"Expected Results/Outcome:", mistakes_content)
                        if mistakes_end:
                            mistakes_content = mistakes_content[:mistakes_end.start()]
                        mistakes_lines = mistakes_content.splitlines()
                        project["common_mistakes"] = [
                            clean_text(line.strip()) for line in mistakes_lines if line.strip()]
                    else:
                        logging.warning("No common mistakes section found.")

                    # Extract expected outcome (fixing extraction range)
                    outcome_start = re.search(r"Expected Results/Outcome:\s*", file_content)
                    if outcome_start:
                        outcome_content = file_content[outcome_start.end():]
                        ref_start = re.search(r"Reference Links:", outcome_content)
                        if ref_start:
                            outcome_content = outcome_content[:ref_start.start()]
                        outcome_lines = outcome_content.splitlines()
                        project["expected_outcome"] = [
                            clean_text(line.strip()) for line in outcome_lines if line.strip()]
                    else:
                        logging.warning("No expected outcome section found.")

                    # Extract reference links
                    ref_start = re.search(r"Reference Links:\s*", file_content)
                    if ref_start:
                        ref_content = file_content[ref_start.end():]
                        ref_lines = ref_content.splitlines()
                        project["reference_links"] = [
                            clean_text(line.strip()) for line in ref_lines if line.strip()]
                    else:
                        logging.warning("No reference links section found.")

                    
                    if project["title"] and project["steps"]:
                        logging.info(f"Inserting project: {project['title']}")
                        collection.insert_one(project)
                    else:
                        logging.warning(f"Skipping invalid project data for: {project['title']}")

            except Exception as e:
                logging.error(f"Error processing file {filename}: {e}")

process_and_insert_to_mongo()


