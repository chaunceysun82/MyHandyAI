import React from "react";

const Star = ({ filled }) => (
	<svg
		viewBox="0 0 20 20"
		className={`h-4 w-4 ${filled ? "text-yellow-500" : "text-gray-300"}`}
		fill="currentColor"
		aria-hidden="true">
		<path d="M10 15.27l-5.18 3.04 1.4-5.99L1 7.97l6.05-.52L10 2l2.95 5.45 6.05.52-5.22 4.35 1.4 5.99L10 15.27z" />
	</svg>
);

export default function RatingStars({ rating, reviews }) {
	const fullStars = Math.floor(rating);
	const emptyStars = 5 - fullStars;

	return (
		<div className="mt-2 w-full flex items-center justify-center gap-1">
			<span className="text-gray-500 text-sm tabular-nums">
				{rating.toFixed(1)}
			</span>
			<div className="flex items-center">
				{Array.from({ length: fullStars }).map((_, i) => (
					<Star key={`full-${i}`} filled />
				))}
				{Array.from({ length: emptyStars }).map((_, i) => (
					<Star key={`empty-${i}`} filled={false} />
				))}
			</div>
			<span className="text-gray-500 text-xs">
				({Number(reviews || 0).toLocaleString()})
			</span>
		</div>
	);
}
