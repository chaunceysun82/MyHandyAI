import React, { useState, useEffect } from "react";
import { getCountries, getStates } from "country-state-picker";

const LocationSelector = ({ value, onChange }) => {
	// Safeguard against null/undefined value
	const safeValue = value || { country: "", state: "" };
	
	const [countryCode, setCountryCode] = useState(safeValue.country || "");
	const [state, setState] = useState(safeValue.state || "");
	const [states, setStates] = useState([]);

	const countries = getCountries();

	useEffect(() => {
		if (countryCode) {
			const fetchedStates = getStates(countryCode);
			setStates(fetchedStates || []);
			setState("");
		} else {
			setStates([]);
			setState("");
		}
	}, [countryCode]);

	const handleCountryChange = (e) => {
		const newCountryCode = e.target.value;
		setCountryCode(newCountryCode);
		onChange({ country: newCountryCode, state: "" });
	};

	const handleStateChange = (e) => {
		const newState = e.target.value;
		setState(newState);
		onChange({ country: countryCode, state: newState });
	};

	return (
		<div className="space-y-6 mt-4 max-w-md mx-auto">
			<div>
				<label className="block text-sm font-medium text-gray-700 mb-1">
					Select your country
				</label>
				<select
					className="w-full border border-gray-300 rounded-lg px-4 py-3 text-base"
					value={countryCode}
					onChange={handleCountryChange}>
					<option value="">Select your country</option>
					{countries.map((c) => (
						<option key={c.code} value={c.code}>
							{c.name}
						</option>
					))}
				</select>
			</div>

			<div>
				<label className="block text-sm font-medium text-gray-700 mb-1">
					Select your state/province
				</label>
				<select
					className="w-full border border-gray-300 rounded-lg px-4 py-3 text-base"
					value={state}
					onChange={handleStateChange}
					disabled={!states.length}>
					<option value="">Select your state/province</option>
					{states.map((s) => (
						<option key={s} value={s}>
							{s}
						</option>
					))}
				</select>
			</div>
		</div>
	);
};

export default LocationSelector;
