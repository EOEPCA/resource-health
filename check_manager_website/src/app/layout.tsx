import type { Metadata } from "next";
import "./globals.css";
import { ChakraProvider } from "@chakra-ui/react"
import { PublicEnvScript } from 'next-runtime-env';

export const metadata: Metadata = {
  title: "Check Manager",
  description: "Check Manager",
};

export default function RootLayout(props: { children: React.ReactNode }) {
  const { children } = props
  return (
    <html suppressHydrationWarning lang="en">
      <head>
        <PublicEnvScript />
      </head>
      <body>
        <ChakraProvider>
          {children}
        </ChakraProvider>
        {/* <Provider>{children}</Provider> */}
      </body>
    </html>
  )
}

