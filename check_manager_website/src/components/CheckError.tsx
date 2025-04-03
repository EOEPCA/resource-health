import { Heading, Text } from "@chakra-ui/react";

export function CheckError(error: Error): JSX.Element {
  return (
    <>
      <Heading>Error occurred</Heading>
      <Text>{`${error.name}: ${error.message}`}</Text>
    </>
  )
}