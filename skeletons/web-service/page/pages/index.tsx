import Image from "next/image";
import type { paths } from "../schema"
import { Inter } from "next/font/google";
import { useEffect, useState } from "react";
import createClient from "openapi-fetch";

const inter = Inter({ subsets: ["latin"] });

export default function Home() {
  const client = createClient<paths>({ baseUrl: "http://localhost:8000" })

  const [apiMessage, setApiMessage] = useState<String>("Loading...")

  useEffect(() => {
    const getApiMessage = async () => {
      const { data, error } = await client.GET("/message")
      if(data) {
        setApiMessage(data.msg)
      } else {
        setApiMessage(`Error ${error}`)
      }
    }
    
    getApiMessage()
  })

  return (
    <main
      className={`flex min-h-screen flex-col items-center justify-between p-24 ${inter.className}`}
    >
      <div>
        <p>
          And now for a message from our API:
        </p>
        <div>{apiMessage}</div>
      </div>
    </main>
  );
}
