import { APIErrors } from "@/lib/backend-wrapper";
import { GetReLoginURL } from "@/lib/config";
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
import { useEffect, useState } from "react";

export type ErrorProps = {
  error: APIErrors | AxiosError | Error;
  reLogin: boolean;
  onRetry?: () => void;
};

export type SetErrorsPropsType = (
  errorsProps: (es: ErrorProps[]) => ErrorProps[]
) => void;

export function DefaultErrorHandler(
  setErrorsProps: SetErrorsPropsType,
  onRetry: () => void
): (error: APIErrors | AxiosError | Error) => void {
  return (error: APIErrors | AxiosError | Error) => {
    const reLogin = error instanceof AxiosError;
    setErrorsProps((errorsProps: ErrorProps[]) => [
      ...errorsProps,
      {
        error: error,
        reLogin: error instanceof AxiosError,
        onRetry: reLogin ? onRetry : undefined,
      },
    ]);
  };
}

export function useError(): {
  errorsProps: ErrorProps[];
  setErrorsProps: SetErrorsPropsType;
  isErrorOpen: boolean;
} {
  const [errorsProps, setErrorsProps] = useState<ErrorProps[]>([]);
  const { isOpen, onOpen, onClose } = useDisclosure();
  useEffect(() => {
    if (errorsProps.length > 0) {
      onOpen();
    } else {
      onClose();
    }
  }, [errorsProps, onOpen, onClose]);
  return {
    errorsProps: errorsProps,
    setErrorsProps: setErrorsProps,
    isErrorOpen: isOpen,
  };
}

type CheckErrorProps = {
  errorsProps: ErrorProps[];
  setErrorsProps: SetErrorsPropsType;
  isOpen: boolean;
};

export function CheckErrorPopup({
  errorsProps,
  setErrorsProps,
  isOpen,
}: CheckErrorProps): JSX.Element {
  const reLoginURL = GetReLoginURL();
  const reLogin = errorsProps.some((errorProps) => errorProps.reLogin);
  const retry = errorsProps.some(
    (errorProps) => errorProps.onRetry !== undefined
  );
  return (
    <>
      <Modal
        onClose={() => setErrorsProps(() => [])}
        isOpen={isOpen}
        isCentered
      >
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Error occurred</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <ErrorDetails
              errors={errorsProps.map((errorProps) => errorProps.error)}
            />
            {reLogin && (
              <Text>
                Relogging in is likely to fix the issue. Return to this page
                after to retry.
              </Text>
            )}
          </ModalBody>
          <ModalFooter>
            {reLogin && (
              <Button mr={3} onClick={() => window.open(reLoginURL, "_blank")}>
                Re Login
              </Button>
            )}
            {retry && (
              <Button
                onClick={() => {
                  setErrorsProps(() => []);
                  errorsProps.forEach((errorProps) => errorProps.onRetry?.());
                }}
              >
                Retry
              </Button>
            )}
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
}

function ErrorDetails({ errors }: { errors: Error[] }): JSX.Element {
  // The element in this state should never be rendered
  if (errors.length === 0) {
    return <Text>Forgot to set error details</Text>;
  }
  // Render just the first error, at least for now
  const error = errors[0];
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
      </>
    );
  }
  return <Text>{`${error.name}: ${error.message}`}</Text>;
}
