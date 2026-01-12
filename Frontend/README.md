# MyHandyAI Frontend

Front-End React application for MyHandyAI, an AI-powered mobile assistant designed to help homeowners with DIY home repairs.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Workflows](#core-workflows)
3. [Visual Workflow Diagrams](#visual-workflow-diagrams)
4. [Key Components](#key-components)
5. [Services & API Layer](#services--api-layer)
6. [Data Flow](#data-flow)
7. [Routing Structure](#routing-structure)
8. [Key Concepts](#key-concepts)
9. [State Management Patterns](#state-management-patterns)
10. [Debugging Tips](#debugging-tips)
11. [Quick Reference](#quick-reference)

---

## Architecture Overview

**Tech Stack:**

- **Framework:** React 19.1.0 with React Router DOM 7.7.1
- **Styling:** Tailwind CSS 3.4.3
- **HTTP Client:** Axios & Fetch API
- **State Management:** React Hooks (useState, useEffect)
- **Build Tool:** Create React App (react-scripts)

**Project Structure:**

```
app/src/
├── pages/           # Main page components
├── components/      # Reusable UI components
├── services/        # API service layer
├── utilities/      # Helper functions
├── styles/         # Global styles
└── assets/         # Static assets (images, SVGs)
```

---

## Core Workflows

### 1. User Authentication & Onboarding Flow

**Path:** `/login` → `/signup` → `/onboarding/*` → `/home`

**Steps:**

1. User lands on `/login` or `/signup`
2. After signup/login, token stored in `localStorage` or `sessionStorage`
3. New users redirected to `/onboarding/` (welcome screen)
4. Onboarding questions collected via `/onboarding/:step`
5. Onboarding data transformed and sent to backend via `signupUserWithOnboarding()`
6. User redirected to `/home` after completion

**Key Files:**

- `pages/auth/Login.jsx` - Login page
- `pages/auth/Signup.jsx` - Signup page
- `pages/onboarding/Onboarding.jsx` - Onboarding flow
- `services/auth.js` - Auth API calls

**API Endpoints Used:**

- `POST /login` - User login
- `POST /users` - User signup (with onboarding data)

---

### 2. Project Creation & Chat Flow

**Path:** `/home` → `/chat` → `/projects/:projectId/overview`

**Steps:**

1. User clicks "Start New Project" on Home page
2. Modal opens to enter project name
3. `createProject(userId, projectName)` called → returns `projectId`
4. User navigated to `/chat` with project state
5. **Chat Page (`Chat.jsx`):**
   - Shows loading spinner while checking generation status
   - Polls `/generation/status/:projectId` endpoint
   - When status = "generation completed", redirects to Project Overview
   - Otherwise shows `ChatWindow` component
6. **ChatWindow Component:**
   - Initializes chat session via `/api/v1/information-gathering-agent/initialize`
   - Stores session ID in localStorage: `sessionId_${userId}_${projectId}`
   - Handles user messages and bot responses
   - Supports image uploads (base64 encoded)
   - When conversation complete (`current_state === "complete"`), shows loading tips
   - Backend generates project steps, tools, and estimations

**Key Files:**

- `pages/Home.jsx` - Project list and creation
- `pages/Chat.jsx` - Chat loading/status page
- `components/Chat/ChatWindow.jsx` - Main chat interface
- `services/projects.js` - Project CRUD operations

**API Endpoints Used:**

- `POST /projects` - Create new project
- `GET /generation/status/:projectId` - Check generation status
- `POST /api/v1/information-gathering-agent/initialize` - Start chat session
- `POST /api/v1/information-gathering-agent/chat/:sessionId` - Send chat messages

---

### 3. Project Overview Flow

**Path:** `/projects/:projectId/overview`

**Steps:**

1. Fetches project data:
   - `fetchSteps(projectId)` → Gets all steps
   - `fetchEstimations(projectId)` → Gets time/cost/skill estimates
2. Displays:
   - **Estimated Breakdown:** Time, cost, skill level
   - **Tools & Materials Card:** First step (always shown)
   - **Step-by-step guidance:** List of all project steps
3. User can:
   - Click any step to view details
   - Click "Next Step" → Goes to Tools page
   - Click "Hi [Name], Need MyHandyAI Assistant?" → Opens ChatWindow2 modal
   - Navigate back to Home

**Key Files:**

- `pages/ProjectOverview.jsx` - Overview page
- `components/StepCard.jsx` - Step card component
- `components/EstimationBreakdown.jsx` - Stats display
- `components/Chat/ChatWindow2.jsx` - Chat modal (different from ChatWindow)
- `services/overview.js` - Overview API calls

**API Endpoints Used:**

- `GET /generation/steps/:projectId` - Fetch project steps
- `GET /generation/estimation/:projectId` - Fetch project estimates

---

### 4. Tools Page Flow

**Path:** `/projects/:projectId/tools`

**Steps:**

1. Fetches tools via `fetchProjectTools(projectId)`
2. Displays tools in grid format with:
   - Tool name, image, price range
   - Required/Optional badges
   - Filter buttons: "All Items", "Required", "Optional"
3. **Selection Mode:**
   - User clicks "Select Tools" → Enters selection mode
   - Can select multiple tools
   - Shows cost estimation for selected tools
   - "Clear All" button to deselect
4. Navigation:
   - "Previous" → Back to Overview
   - "Next Step" → Goes to first actual step (`/steps/1`)

**Key Files:**

- `pages/ToolsPage.jsx` - Tools page
- `components/tools/ToolGrid.jsx` - Tools grid display
- `components/steps/ToolsLayout.jsx` - Layout wrapper
- `services/tools.js` - Tools API calls

**API Endpoints Used:**

- `GET /tools/:projectId` - Fetch project tools

---

### 5. Step Page Flow

**Path:** `/projects/:projectId/steps/:stepIndex`

**Steps:**

1. Fetches all steps via `fetchSteps(projectId)`
2. Extracts specific step using `extractSpecificStep(stepsData, stepIndex)`
3. Transforms step data using `transformStepData()` for display
4. Displays step details:
   - **Header:** Step number, title, progress indicator
   - **Time Estimate:** With feedback buttons (thumbs up/down)
   - **Media Guide:** Video (project-level) and images
   - **Instructions:** Formatted step instructions
   - **Tools Needed:** List of tools for this step
   - **Safety Warnings:** Safety information
   - **Pro Tips:** Helpful tips
   - **Completion Confirmation:** Checkbox to mark step complete
5. **Step Completion:**
   - User marks step complete → `toggleStepCompletion(projectId, stepNumber)`
   - Progress updates in real-time
   - If all steps complete → Can navigate to Project Completed page
6. Navigation:
   - "Previous" → Previous step (or Tools if on step 1)
   - "Next Step" → Next step (or Completed page if last step)

**Key Files:**

- `pages/StepPage.jsx` - Step detail page
- `components/steps/*` - Step-specific components
- `services/steps.js` - Step API calls
- `utilities/StepUtils.js` - Step data transformation helpers

**API Endpoints Used:**

- `GET /generation/steps/:projectId` - Fetch all steps
- `PUT /complete-step/:projectId/:stepNumber` - Mark step complete
- `PUT /reset-step/:projectId/:stepNumber` - Undo step completion
- `PUT /step-feedback/:projectId/:stepNumber/:feedback` - Submit feedback (1=good, 0=bad)

---

### 6. Project Management Flow

**Path:** `/home` (Project List)

**Features:**

1. **Project List:**
   - Fetches all projects via `fetchProjects(userId)`
   - For each project, fetches progress via `fetchProjectProgress(projectId)`
   - Displays projects with progress percentage
2. **Tabs:**
   - "Ongoing" - Projects with progress < 100%
   - "Completed" - Projects with progress >= 100%
3. **Search & Filter:**
   - Search bar to filter projects by name
   - Filter menu with options
4. **Project Actions:**
   - **Start Chat:** Navigate to `/chat` with project
   - **Rename:** Update project title via `updateProject()`
   - **Complete:** Mark entire project complete via `completeProject()`
   - **Delete:** Remove project via `deleteProject()`

**Key Files:**

- `pages/Home.jsx` - Home page
- `components/ProjectCard.jsx` - Project card component
- `services/projects.js` - Project management APIs

**API Endpoints Used:**

- `GET /projects?user_id=:userId` - Fetch user's projects
- `GET /project/:projectId/progress` - Get project progress (0-1, converted to %)
- `PUT /project/:projectId/complete` - Mark project complete
- `PUT /projects/:projectId` - Update project
- `DELETE /projects/:projectId` - Delete project

---

## Visual Workflow Diagrams

### Authentication & Onboarding Workflow

```
┌─────────────┐
│   Login     │
│   /login    │
└──────┬──────┘
       │
       ├─── Existing User ────┐
       │                      │
       └─── New User          │
              │               │
              ▼               │
       ┌─────────────┐        │
       │   Signup    │        │
       │   /signup   │        │
       └──────┬──────┘        │
              │               │
              ▼               │
       ┌─────────────┐        │
       │ Onboarding  │        │
       │  Welcome    │        │
       └──────┬──────┘        │
              │               │
              ▼               │
       ┌─────────────┐        │
       │ Onboarding  │◄───────┘
       │  Questions  │
       │ /onboarding │
       │   /:step    │
       └──────┬──────┘
              │
              ▼
       ┌─────────────┐
       │ Onboarding │
       │  Complete  │
       └──────┬──────┘
              │
              ▼
       ┌─────────────┐
       │    Home     │
       │   /home     │
       └─────────────┘
```

---

### Project Creation Workflow

```
┌─────────────┐
│    Home     │
│   /home     │
└──────┬──────┘
       │
       │ User clicks "Start New Project"
       │
       ▼
┌─────────────┐
│ Create      │
│ Project     │
│ Modal       │
└──────┬──────┘
       │
       │ User enters project name
       │
       ▼
┌─────────────┐
│ POST        │
│ /projects   │
└──────┬──────┘
       │
       │ Returns projectId
       │
       ▼
┌─────────────┐
│    Chat     │
│   /chat     │
└──────┬──────┘
       │
       │ Check generation status
       │ GET /generation/status/:projectId
       │
       ├─── Not Complete ────┐
       │                      │
       │                      ▼
       │              ┌─────────────┐
       │              │ ChatWindow  │
       │              │ Component   │
       │              └──────┬──────┘
       │                     │
       │                     │ Initialize session
       │                     │ POST /api/v1/information-gathering-agent/initialize
       │                     │
       │                     ▼
       │              ┌─────────────┐
       │              │ User chats   │
       │              │ with AI      │
       │              │ POST /chat   │
       │              └──────┬──────┘
       │                     │
       │                     │ AI processes & generates
       │                     │ steps, tools, estimations
       │                     │
       │                     ▼
       │              ┌─────────────┐
       │              │ Poll Status │
       │              │ (every 800ms)│
       │              └──────┬──────┘
       │                     │
       └─── Complete ────────┘
              │
              ▼
       ┌─────────────┐
       │  Project    │
       │  Overview   │
       │ /projects/  │
       │  :id/       │
       │  overview   │
       └─────────────┘
```

---

### Project Overview Workflow

```
┌─────────────┐
│  Project    │
│  Overview   │
│ /projects/  │
│  :id/       │
│  overview   │
└──────┬──────┘
       │
       │ Fetch data on mount
       │
       ├─── GET /generation/steps/:projectId
       ├─── GET /generation/estimation/:projectId
       │
       ▼
┌─────────────┐
│  Display    │
│  Components │
└──────┬──────┘
       │
       ├─── Estimated Breakdown (Time, Cost, Skill)
       ├─── Tools & Materials Card
       ├─── Step-by-step Guidance List
       │
       │ User Actions:
       │
       ├─── Click Step Card ────► Navigate to StepPage
       │
       ├─── Click "Next Step" ────► Navigate to ToolsPage
       │
       ├─── Click "Assistant" ────► Open ChatWindow2 Modal
       │
       └─── Click "Previous" ────► Navigate to Home
```

---

### Tools Page Workflow

```
┌─────────────┐
│  Tools      │
│  Page       │
│ /projects/  │
│  :id/tools  │
└──────┬──────┘
       │
       │ Fetch tools on mount
       │ GET /tools/:projectId
       │
       ▼
┌─────────────┐
│  Display    │
│  Tools Grid │
└──────┬──────┘
       │
       │ Filter Options:
       │ - All Items
       │ - Required
       │ - Optional
       │
       │ User Actions:
       │
       ├─── Click "Select Tools" ────► Enter Selection Mode
       │                                 │
       │                                 ├─── Select tools
       │                                 ├─── View cost estimation
       │                                 └─── "Clear All" to deselect
       │
       ├─── Click "Previous" ────► Navigate to Overview
       │
       └─── Click "Next Step" ────► Navigate to StepPage (step 1)
```

---

### Step Page Workflow

```
┌─────────────┐
│  Step Page  │
│ /projects/  │
│  :id/steps/ │
│  :stepIndex │
└──────┬──────┘
       │
       │ Fetch step data on mount
       │ GET /generation/steps/:projectId
       │
       ▼
┌─────────────┐
│  Extract    │
│  Step Data  │
│  (StepUtils)│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Display    │
│  Step Info  │
└──────┬──────┘
       │
       ├─── Header (Step #, Title, Progress)
       ├─── Time Estimate (with feedback)
       ├─── Media Guide (Video + Images)
       ├─── Instructions
       ├─── Tools Needed
       ├─── Safety Warnings
       ├─── Pro Tips
       └─── Completion Checkbox
       │
       │ User Actions:
       │
       ├─── Mark Step Complete ────► PUT /complete-step/:projectId/:stepNumber
       │                                 │
       │                                 ├─── Refresh step data
       │                                 ├─── Update progress
       │                                 └─── If all complete → Show "Project Complete"
       │
       ├─── Submit Feedback ────► PUT /step-feedback/:projectId/:stepNumber/:feedback
       │
       ├─── Click "Previous" ────► Navigate to previous step (or Tools if step 1)
       │
       └─── Click "Next Step" ────► Navigate to next step (or Completed if last step)
```

---

### Home Page (Project Management) Workflow

```
┌─────────────┐
│    Home     │
│   /home     │
└──────┬──────┘
       │
       │ On mount:
       │ GET /projects?user_id=:userId
       │
       │ For each project:
       │ GET /project/:projectId/progress
       │
       ▼
┌─────────────┐
│  Display    │
│  Projects   │
└──────┬──────┘
       │
       │ Tabs:
       │ - Ongoing (progress < 100%)
       │ - Completed (progress >= 100%)
       │
       │ Search & Filter:
       │ - Search by project name
       │ - Filter menu options
       │
       │ Project Actions (on ProjectCard):
       │
       ├─── Click Project ────► Navigate to /chat (resume project)
       │
       ├─── Click "Rename" ────► PUT /projects/:projectId
       │                          Update project title
       │
       ├─── Click "Complete" ────► PUT /project/:projectId/complete
       │                            Mark all steps complete
       │                            Refresh project list
       │
       └─── Click "Delete" ────► DELETE /projects/:projectId
                                  Remove from list
```

---

### Chat Components Comparison

**ChatWindow (Used in `/chat` page)**

```
Purpose: Initial project creation chat
Location: pages/Chat.jsx
API: /api/v1/information-gathering-agent
Features:
- Full-screen chat interface
- Image upload support
- Session persistence (localStorage)
- Message history caching
- Owned tools tracking
- Loading tips during generation
```

**ChatWindow2 (Used in Overview/Step pages)**

```
Purpose: Contextual help chat
Location: components/Chat/ChatWindow2.jsx
API: /api/v1/step-guidance (or similar)
Features:
- Modal overlay
- Project/step-specific context
- Quick help for current step
- No session persistence
```

---

## Key Components

### Page Components (`pages/`)

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| `Home.jsx` | Project dashboard | Project list, search, filters, create project |
| `Chat.jsx` | Chat loading/status | Polls generation status, shows loading tips |
| `ProjectOverview.jsx` | Project summary | Steps list, estimations, tools card, chat modal |
| `StepPage.jsx` | Step details | Full step instructions, media, completion |
| `ToolsPage.jsx` | Tools & materials | Tool grid, selection mode, cost estimation |
| `Login.jsx` / `Signup.jsx` | Authentication | User login/signup |
| `Onboarding.jsx` | User onboarding | Multi-step questionnaire |

### Reusable Components (`components/`)

**Chat Components:**

- `ChatWindow.jsx` - Main chat interface (used in Chat page)
- `ChatWindow2.jsx` - Chat modal (used in Overview/Step pages)
- `MessageList.jsx` - Message display
- `ChatInput.jsx` - Message input with image upload
- `QuickReplyButtons.jsx` - Suggested message buttons

**Step Components:**

- `StepCard.jsx` - Step card in overview list
- `StepHeader.jsx` - Step page header
- `StepFooter.jsx` - Step navigation buttons
- `StepInstructions.jsx` - Formatted instructions
- `StepMediaGuide.jsx` - Video/image display
- `StepCompletionConfirmation.jsx` - Completion checkbox

**Other Components:**

- `ProjectCard.jsx` - Project card in home list
- `Header.jsx` - Page header
- `SideNavbar.jsx` - Side navigation menu
- `MobileWrapper.jsx` - Mobile layout wrapper
- `LoadingPlaceholder.jsx` - Loading state

---

## Services & API Layer

### Service Files (`services/`)

#### `projects.js`

**Functions:**

- `fetchProjects(userId)` - Get all user projects with progress
- `createProject(userId, projectTitle)` - Create new project
- `deleteProject(projectId)` - Delete project
- `updateProject(projectId, updateData)` - Update project
- `completeProject(projectId)` - Mark project complete
- `fetchProjectProgress(projectId)` - Get progress (0-1 → %)

#### `steps.js`

**Functions:**

- `getStepDetails(projectId, stepNumber)` - Get step details
- `toggleStepCompletion(projectId, stepNumber)` - Toggle step complete
- `resetStepCompletion(projectId, stepNumber)` - Undo step completion
- `updateStepProgress(projectId, stepNumber, progressData)` - Update progress
- `submitStepFeedback(projectId, stepNumber, feedback)` - Submit feedback (1/0)

#### `overview.js`

**Functions:**

- `fetchSteps(projectId)` - Get all project steps
- `fetchEstimations(projectId)` - Get time/cost/skill estimates

#### `tools.js`

**Functions:**

- `fetchProjectTools(projectId)` - Get project tools
- `transformToolsData(rawData)` - Transform API response

#### `auth.js`

**Functions:**

- `loginUser(email, password)` - User login
- `signupUserWithOnboarding(userData, onboardingAnswers)` - Signup with onboarding
- `getUserById(userId)` - Get user details
- `hasCompletedOnboarding(user)` - Check onboarding status

---

## Data Flow

### Project Creation Flow

```
User Input (Project Name)
    ↓
createProject() → POST /projects
    ↓
Backend creates project → Returns projectId
    ↓
Navigate to /chat with projectId
    ↓
ChatWindow initializes → POST /api/v1/information-gathering-agent/initialize
    ↓
User chats with AI → POST /api/v1/information-gathering-agent/chat/:sessionId
    ↓
Backend processes → Generates steps, tools, estimations
    ↓
Poll status → GET /generation/status/:projectId
    ↓
When complete → Navigate to /projects/:projectId/overview
```

### Step Completion Flow

```
User marks step complete
    ↓
toggleStepCompletion() → PUT /complete-step/:projectId/:stepNumber
    ↓
Backend updates step status
    ↓
Refresh step data → GET /generation/steps/:projectId
    ↓
Update UI with new completion status
    ↓
If all steps complete → Show "Project Complete" option
```

### Progress Tracking Flow

```
Home page loads
    ↓
fetchProjects() → GET /projects?user_id=:userId
    ↓
For each project → fetchProjectProgress() → GET /project/:projectId/progress
    ↓
Backend calculates: completedSteps / totalSteps (0-1)
    ↓
Convert to percentage (0-100%)
    ↓
Display in ProjectCard with progress bar
```

### Project Lifecycle

```
Create → Chat → Generate → Overview → Tools → Steps → Complete
  │        │        │         │         │       │        │
  │        │        │         │         │       │        │
  POST    Chat    Backend   Display   Display  Execute  Track
  /projects  API   Process   Steps     Tools    Steps    Progress
```

### Step Completion Flow

```
User Action → API Call → Backend Update → Refresh Data → UI Update
     │            │            │              │            │
  Checkbox    PUT /complete   Database    GET /steps   Progress
              -step           Update      Refresh      Bar Update
```

### Progress Tracking

```
Home Load → Fetch Projects → For Each Project → Fetch Progress → Display
    │            │                  │                │            │
  useEffect   GET /projects      projectId      GET /progress   Card
                                      │              │
                                      │              │
                              Calculate %       0-1 → 0-100%
```

---

## Routing Structure

**Route Configuration** (`App.js`):

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | Redirect | Auto-redirect based on auth |
| `/login` | `Login` | User login |
| `/signup` | `Signup` | User signup |
| `/home` | `Home` | Project dashboard |
| `/chat` | `Chat` | Chat interface (project creation) |
| `/onboarding/` | `OnboardingWelcome` | Onboarding welcome |
| `/onboarding/:step` | `Onboarding` | Onboarding questions |
| `/onboarding/complete` | `OnboardingComplete` | Onboarding done |
| `/projects/:projectId/overview` | `ProjectOverview` | Project summary |
| `/projects/:projectId/steps/:stepIndex` | `StepPage` | Step details |
| `/projects/:projectId/tools` | `ToolsPage` | Tools & materials |
| `/projects/:projectId/completed` | `ProjectCompleted` | Project completion |
| `/projects/:projectId/feedback` | `Feedback` | Project feedback |

**Navigation Patterns:**

- **State Passing:** Uses React Router `state` prop to pass data between routes
- **Protected Routes:** Auth check in `App.js` useEffect
- **Deep Linking:** All routes support direct navigation via URL

### Key Navigation Patterns

**Forward Navigation:**

```
Home → Chat → Overview → Tools → Step 1 → Step 2 → ... → Completed
```

**Backward Navigation:**

```
Any Page → Previous Button → Previous Page
Step 1 → Previous → Tools
Tools → Previous → Overview
Overview → Close → Home
```

**Modal Navigation:**

```
Overview → Assistant Button → ChatWindow2 Modal
Step Page → Assistant Button → ChatWindow2 Modal
```

---

## Key Concepts

### Session Management

- Chat sessions stored in localStorage: `sessionId_${userId}_${projectId}`
- Messages cached: `messages_${userId}_${projectId}`
- Owned tools cached: `owned_tools_${userId}_${projectId}`

### Step Indexing

- **UI Display:** Step 1 = Tools, Step 2 = First project step, etc.
- **Backend API:** Step 0 = Tools, Step 1 = First project step, etc.
- **URL Routing:** `/steps/1` = First project step (backend index 0)
- Conversion handled in `StepPage.jsx` and `StepUtils.js`

### Progress Calculation

- Backend returns progress as decimal (0.0 - 1.0)
- Frontend converts to percentage (0% - 100%)
- Formula: `Math.round(progress * 100)`

### Image Handling

- Images uploaded as base64 strings
- MIME type included: `image_base64` + `image_mime_type`
- Supported in ChatWindow for project creation

---

## State Management Patterns

### Local State (useState)

- Component-specific UI state
- Form inputs
- Modal visibility
- Loading states

### Session Storage (localStorage/sessionStorage)

- Auth tokens
- Display names
- Chat sessions
- Message history
- Owned tools

### URL State (React Router)

- Project IDs
- Step indices
- Navigation state passed via `state` prop

### Server State (API Calls)

- Projects list
- Steps data
- Tools data
- Progress calculations
- Estimations

---

## Deprecated/Unused Code

**Note:** The codebase contains some commented-out code and alternative implementations. Focus on:

- Active routes in `App.js`
- Components actually imported and used
- Service functions that are called
- API endpoints that return data

**Common Patterns to Avoid:**

- Old API endpoints (commented out in `overview.js`)
- Unused state variables
- Commented-out navigation logic

---

## Environment Variables

**Required:**

- `REACT_APP_BASE_URL` - Backend API base URL

**Usage:**

- All service files use `process.env.REACT_APP_BASE_URL`
- Must be set in `.env` file or build environment

---

## Debugging Tips

### Common Issues

1. **Step Index Mismatch:**
   - UI shows Step 1 = Tools, Step 2 = First project step
   - Backend API uses Step 0 = Tools, Step 1 = First project step
   - Check `StepUtils.js` for conversion logic

2. **Progress Not Updating:**
   - Check `fetchProjectProgress()` returns 0-1 decimal
   - Verify conversion to percentage: `Math.round(progress * 100)`
   - Check backend endpoint: `/project/:projectId/progress`

3. **Chat Session Lost:**
   - Check localStorage keys: `sessionId_${userId}_${projectId}`
   - Verify session ID is saved after initialization
   - Check API endpoint: `/api/v1/information-gathering-agent/thread/:projectId`

4. **Navigation State Missing:**
   - Always pass state via React Router `navigate(path, { state: {...} })`
   - Check `useLocation().state` in destination component
   - Fallback to localStorage if needed

---

## Quick Reference

### API Base URL

```javascript
const API_BASE = process.env.REACT_APP_BASE_URL;
```

### Common Service Imports

```javascript
import { fetchProjects, createProject } from '../services/projects';
import { fetchSteps } from '../services/overview';
import { toggleStepCompletion } from '../services/steps';
import { fetchProjectTools } from '../services/tools';
```

### Common Navigation Pattern

```javascript
navigate(`/projects/${projectId}/overview`, {
  state: { projectId, projectName, userName }
});
```

### Common Data Fetching Pattern

```javascript
useEffect(() => {
  let cancelled = false;
  (async function run() {
    const data = await fetchData(projectId);
    if (!cancelled) setData(data);
  })();
  return () => { cancelled = true; };
}, [projectId]);
```

---

## Summary

**MyHandyAI Frontend** is a React-based mobile-first application that guides users through DIY home repair projects. The main flow is:

1. **Authenticate** → Login/Signup with optional onboarding
2. **Create Project** → Chat with AI to describe the problem
3. **View Overview** → See generated steps, tools, and estimates
4. **Follow Steps** → Complete each step with detailed guidance
5. **Track Progress** → Monitor completion and get feedback

The architecture is clean, component-based, and uses React Router for navigation with state passing for data flow between pages.
