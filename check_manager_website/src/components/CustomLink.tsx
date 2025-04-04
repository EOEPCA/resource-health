import NextLink from "next/link";
import { Link } from "@chakra-ui/react";

// export const CustomLink: typeof Link = (props) => {
//   return <Link as={NextLink} {...props}></Link>;
// };

type CustomLinkProps = {
  children: string;
  href: string;
  className?: string;
};

export default function CustomLink({
  children,
  ...props
}: CustomLinkProps): JSX.Element {
  return (
    <Link as={NextLink} {...props}>
      {children}
    </Link>
  );
}
