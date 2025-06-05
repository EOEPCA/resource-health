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
  children: React.ReactNode;
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
      <main className="flex min-h-screen flex-col items-start p-24 gap-2">
        {children}
      </main>
    </ThemeProvider>
  );
}
