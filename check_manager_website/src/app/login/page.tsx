"use client";

import DefaultLayout from "@/layouts/DefaultLayout";
import { Heading, Text } from "@chakra-ui/react";
import { useEffect, useState } from "react";

export default function Login(): JSX.Element {
  const [couldClose, setCouldClose] = useState(false);
  const [secsRemaining, setSecsRemaining] = useState(5);
  useEffect(() => {
    // window should only be accessed on the client side, and this is one way to achieve that
    setCouldClose(!!window.opener);
  }, []);
  useEffect(() => {
    if (!couldClose) {
      return;
    }
    if (secsRemaining <= 0) {
      window.close();
    } else {
      setTimeout(() => setSecsRemaining(secsRemaining - 1), 1000);
    }
  }, [secsRemaining, couldClose]);
  return (
    <DefaultLayout>
      <Heading>Login successful</Heading>
      {couldClose && <Text>The tab will close in {secsRemaining} seconds</Text>}
    </DefaultLayout>
  );
}
