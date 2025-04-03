import { CSSReset, theme, ThemeProvider } from "@chakra-ui/react";

export default function DefaultLayout({children}: {children: JSX.Element | JSX.Element[]}): JSX.Element {
  return (
    <ThemeProvider theme={theme}>
      <CSSReset />
      <main className="flex min-h-screen flex-col items-start p-24">
        {/* <p>Hello there</p> */}
        {children}
      </main>
    </ThemeProvider>
  )
}