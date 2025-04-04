import {
  CSSReset,
  defineStyleConfig,
  extendTheme,
  ThemeProvider,
} from "@chakra-ui/react";

const Link = defineStyleConfig({
  baseStyle: {
    textDecoration: "underline",
  },
});

export default function DefaultLayout({
  children,
}: {
  children: JSX.Element | JSX.Element[];
}): JSX.Element {
  return (
    <ThemeProvider
      theme={extendTheme({
        components: {
          Link,
        },
      })}
    >
      <CSSReset />
      <main className="flex min-h-screen flex-col items-start p-24">
        {/* <p>Hello there</p> */}
        {children}
      </main>
    </ThemeProvider>
  );
}
