import { FetchState } from "@/lib/helpers";
import { Text, Spinner } from "@chakra-ui/react";

export function LoadingText({
  text,
  fetchState,
}: {
  text: string | number;
  fetchState: FetchState;
}): JSX.Element {
  return (
    <div className="flex flex-row gap-2">
      <Text>{text}</Text>
      {fetchState === "Loading" && <Spinner />}
    </div>
  );
}
