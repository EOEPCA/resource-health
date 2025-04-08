import { Button } from "@chakra-ui/react";
import { useState } from "react";
import { IoCheckmarkCircle as Checkmark } from "react-icons/io5";

type ButtonWithCheckmarkProps = {
  children: string;
  onClick: () => void;
};

// Shows a checkmark next to the button when it is clicked
export default function ButtonWithCheckmark({
  children,
  onClick,
  ...props
}: ButtonWithCheckmarkProps): JSX.Element {
  const [buttonClicked, setButtonClicked] = useState(false);
  return (
    <div className="flex flex-row gap-1 items-center">
      <Button
        onClick={() => {
          onClick();
          setButtonClicked(true);
        }}
        {...props}
      >
        {children}
      </Button>
      {buttonClicked && <Checkmark />}
    </div>
  );
}
