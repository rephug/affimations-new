// src/components/common/TimezoneSelect.js
import React from "react";
import { Select } from "@chakra-ui/react";

const TimezoneSelect = ({ value, onChange }) => {
  // Common timezones - you can expand this list
  const timezones = [
    { value: "America/New_York", label: "Eastern Time (ET)" },
    { value: "America/Chicago", label: "Central Time (CT)" },
    { value: "America/Denver", label: "Mountain Time (MT)" },
    { value: "America/Los_Angeles", label: "Pacific Time (PT)" },
    { value: "Europe/London", label: "London (GMT)" },
    { value: "Europe/Paris", label: "Paris (CET)" },
    { value: "Asia/Tokyo", label: "Tokyo (JST)" }
  ];

  return (
    <Select value={value} onChange={onChange}>
      {timezones.map(tz => (
        <option key={tz.value} value={tz.value}>
          {tz.label}
        </option>
      ))}
    </Select>
  );
};

export default TimezoneSelect;