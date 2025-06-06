import { durationStringToDuration } from "@/lib/helpers";
import { Select, Text } from "@chakra-ui/react";

export type TelemetryDurationDropdownProps = {
  durationString: string;
  setDurationString: (value: string) => void;
};

export function TelemetryDurationTextAndDropdown({
  durationString,
  setDurationString,
}: TelemetryDurationDropdownProps): JSX.Element {
  return (
    <div className="flex flex-row gap-1 items-center">
      <Text className="whitespace-nowrap">Displaying data from the last</Text>
      <Select
        value={durationString}
        onChange={(e) => setDurationString(e.target.value)}
      >
        {durationStringToDuration
          .keys()
          .map((durationString) => (
            <option key={durationString} value={durationString}>
              {durationString}
            </option>
          ))
          .toArray()}
      </Select>
    </div>
  );
}
