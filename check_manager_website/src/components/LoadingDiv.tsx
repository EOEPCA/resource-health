import { FetchState } from "@/lib/helpers";
import { Spinner } from "@chakra-ui/react";
import { ReactNode } from "react";

export function LoadingDiv({
  fetchState,
  children,
  className,
}: {
  fetchState: FetchState;
  children: ReactNode;
  className?: string;
}): JSX.Element {
  return (
    <div
      className={
        "flex flex-row gap-2 items-center " + (className ? className : "")
      }
    >
      {children}
      {fetchState === "Loading" && <Spinner />}
    </div>
  );
}
