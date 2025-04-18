import { APIError, APIErrorResponse } from "@/lib/backend-wrapper";
import {
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
  Text,
  useDisclosure,
} from "@chakra-ui/react";
import { AxiosError } from "axios";
import { useState } from "react";

export function useError(): [JSX.Element, (error: Error) => void] {
  const [error, setErrorSlim] = useState<Error | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  function setError(error: Error | null) {
    setErrorSlim(error);
    if (error !== null) {
      onOpen();
    }
  }
  return [
    // eslint-disable-next-line react/jsx-key
    <CheckErrorPopup error={error} isOpen={isOpen} onClose={onClose} />,
    setError,
  ] as const;
}

type CheckErrorProps = {
  error: Error | AxiosError | null;
  isOpen: boolean;
  onClose: () => void;
};

function CheckErrorPopup({
  error,
  isOpen,
  onClose,
}: CheckErrorProps): JSX.Element {
  return (
    <>
      <Modal onClose={onClose} isOpen={isOpen} isCentered>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Error occurred</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <ErrorDetails error={error} />
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
}

function ErrorDetails({
  error,
}: {
  error: Error | AxiosError<APIErrorResponse> | null;
}): JSX.Element {
  // The element in this state should never be rendered
  if (error === null) {
    return <Text>Forgot to set error details</Text>;
  }
  if (error.name == "AxiosError") {
    const axiosError = error as AxiosError;
    if (
      axiosError.response &&
      axiosError.response.data instanceof Object &&
      "errors" in axiosError.response.data
    ) {
      const errors = axiosError.response.data.errors as APIError[];
      return (
        <>
          {errors.map((error, ind) => (
            <Text key={ind} className="whitespace-pre">
              {error.title} (code {error.status}): {error.detail}
            </Text>
          ))}
        </>
      );
    }
    const statusStr = axiosError.status ? ` (code ${axiosError.status})` : "";
    return (
      <>
        <Text>
          {axiosError.name}
          {statusStr}: {axiosError.message}
        </Text>
        <Text>
          Relogging in is likely to fix the issue. You can do so by refreshing
          this page, but any data you have might entered will be lost.
        </Text>
      </>
    );
  }
  return <Text>{`${error.name}: ${error.message}`}</Text>;
}
