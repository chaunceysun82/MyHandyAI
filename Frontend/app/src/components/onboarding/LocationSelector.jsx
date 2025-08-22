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
					className="w-full border border-gray-300 rounded-lg p-2 text-base appearance-none bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					style={{
						WebkitAppearance: 'none',
						MozAppearance: 'none',
						appearance: 'none',
						backgroundImage: 'url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23007CB2%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.1c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.4-12.8z%22/%3E%3C/svg%3E")',
						backgroundRepeat: 'no-repeat',
						backgroundPosition: 'right 8px center',
						backgroundSize: '12px auto',
						paddingRight: '40px'
					}}
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
					className="w-full border border-gray-300 rounded-lg p-2 text-base appearance-none bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					style={{
						WebkitAppearance: 'none',
						MozAppearance: 'none',
						appearance: 'none',
						backgroundImage: 'url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23007CB2%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.1c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.4-12.8z%22/%3E%3C/svg%3E")',
						backgroundRepeat: 'no-repeat',
						backgroundPosition: 'right 8px center',
						backgroundSize: '12px auto',
						paddingRight: '40px'
					}}
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
