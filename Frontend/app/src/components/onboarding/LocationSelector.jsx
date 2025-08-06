import React, { useState, useEffect } from "react";
import { getCountries, getStates } from "country-state-picker";

const LocationSelector = ({ value, onChange }) => {
	const [countryCode, setCountryCode] = useState(value?.country || "");
	const [state, setState] = useState(value?.state || "");
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

	useEffect(() => {
		onChange({ country: countryCode, state });
	}, [countryCode, state, onChange]);

	return (
		<div className="space-y-6 mt-4 max-w-md mx-auto">
			<div>
				<label className="block text-sm font-medium text-gray-700 mb-1">
					Select your country
				</label>
				<select
					className="w-full border border-gray-300 rounded-lg px-4 py-3 text-base"
					value={countryCode}
					onChange={(e) => setCountryCode(e.target.value)}>
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
					onChange={(e) => setState(e.target.value)}
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
