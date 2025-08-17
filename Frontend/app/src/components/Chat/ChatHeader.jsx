export default function ChatHeader({ onClose, theme, onThemeToggle, SunIcon, MoonIcon, dragHandleProps = {} }) {
	return (
		<header className="relative px-5 pt-3 pb-2 select-none">
			{/* notch / drag handle */}
			<div
				className="mx-auto mt-2 h-1.5 w-32 rounded-full bg-[#000000] cursor-grab active:cursor-grabbing touch-none"
				{...dragHandleProps}
			/>
			{/* close */}
			<button
				aria-label="Close"
				onClick={onClose}
				className="absolute right-4 top-8 text-[32px] leading-none text-black hover:text-gray-600">
				×
			</button>
			<h1 className="mt-3 mb-3 text-center text-[20px] font-semibold text-[#000000]">
				MyHandyAI Assistant
			</h1>
			<p className="text-center text-[#595959] text-[12px] font-regular text-sm text-gray-500">
				Let’s start by understanding your problem!
			</p>
		</header>
	);
}
