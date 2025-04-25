import { APIErrors } from "@/lib/backend-wrapper";
import { GetReLoginURL } from "@/lib/helpers";
import {
  Button,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Text,
  useDisclosure,
} from "@chakra-ui/react";
import { AxiosError } from "axios";
import { useState } from "react";

export type ErrorProps = {
  error: APIErrors | AxiosError | Error;
  reLogin: boolean;
  onRetry?: () => void;
};

export type SetErrorPropsType = (errorProps: ErrorProps | null) => void;

export function DefaultErrorHandler(
  setErrorProps: SetErrorPropsType,
  onRetry: () => void
): (error: APIErrors | AxiosError | Error) => void {
  return (error: APIErrors | AxiosError | Error) => {
    const reLogin = error instanceof AxiosError;
    setErrorProps({
      error: error,
      reLogin: error instanceof AxiosError,
      onRetry: reLogin ? onRetry : undefined,
    });
  };
}

export function useError(): {
  errorProps: ErrorProps | null;
  setErrorProps: SetErrorPropsType;
  isErrorOpen: boolean;
  onErrorClose: () => void;
} {
  const [errorProps, setErrorPropsSlim] = useState<ErrorProps | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  function setErrorProps(errorProps: ErrorProps | null) {
    setErrorPropsSlim(errorProps);
    if (errorProps !== null) {
      onOpen();
    }
  }
  return {
      errorProps: errorProps,
    setErrorProps: setErrorProps,
    isErrorOpen: isOpen,
    onErrorClose: onClose,
  };
}

type CheckErrorProps = {
  errorProps: ErrorProps | null;
  isOpen: boolean;
  onClose: () => void;
};

export function CheckErrorPopup({
  errorProps,
  isOpen,
  onClose,
}: CheckErrorProps): JSX.Element {
  const reLoginURL = GetReLoginURL();
  return (
    <>
      <Modal onClose={onClose} isOpen={isOpen} isCentered>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Error occurred</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <ErrorDetails error={errorProps ? errorProps.error : null} />
          </ModalBody>
          {errorProps !== null && (
            <ModalFooter>
              {errorProps.reLogin && (
                <Button
                  mr={3}
                  onClick={() => window.open(reLoginURL, "_blank")}
                >
                  Re Login
                </Button>
              )}
              {errorProps.onRetry && (
                <Button
                  onClick={() => {
                    onClose();
                    errorProps.onRetry!();
                  }}
                >
                  Retry
                </Button>
              )}
            </ModalFooter>
          )}
        </ModalContent>
      </Modal>
    </>
  );
}

function ErrorDetails({ error }: { error: Error | null }): JSX.Element {
  // The element in this state should never be rendered
  if (error === null) {
    return <Text>Forgot to set error details</Text>;
  }
  if (error instanceof APIErrors) {
    return (
      <>
        {error.errors.map((error, ind) => (
          <Text key={ind} className="whitespace-pre">
            {error.title} (code {error.status}): {error.detail}
          </Text>
        ))}
      </>
    );
  }
  if (error instanceof AxiosError) {
    const statusStr = error.status ? ` (code ${error.status})` : "";
    return (
      <>
        <Text>
          {error.name}
          {statusStr}: {error.message}
        </Text>
        <Text>
          Relogging in is likely to fix the issue. Return to this page after to
          retry.
        </Text>
      </>
    );
  }
  return <Text>{`${error.name}: ${error.message}`}</Text>;
}
