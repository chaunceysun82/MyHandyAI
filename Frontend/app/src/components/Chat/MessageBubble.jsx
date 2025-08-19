export default function MessageBubble({ role = "bot", children }) {
	if (role === "bot") {
		return (
			<div className="mt-4 flex items-start gap-2">
				<div className="h-7 w-7 rounded-full bg-gray-200 flex items-center justify-center shrink-0">
					<span className="text-xs">🤖</span>
				</div>
				<div className="max-w-[78%] text-[15px] rounded-xl bg-gray-200 px-3.5 py-2.5 leading-snug text-gray-800">
					{children}
				</div>
			</div>
		);
	}
	return (
		<div className="mt-3 flex justify-end">
			<div className="max-w-[78%] rounded-xl bg-[#2F87FF] text-white px-3.5 py-2.5 text-[15px] leading-snug whitespace-pre-wrap">
				{children}
			</div>
		</div>
	);
}
