import { Terminal } from "lucide-react"
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"

export default function Home() {
  return (
    <>
    <div className="flex items-center justify-center min-h-screen">
      <div className="max-w-md w-full p-6 bg-background border rounded-lg shadow-lg">
        <Terminal className="h-4 w-4"/>
        <Alert variant={"default"}>
          <AlertTitle>twinyn</AlertTitle>
          <AlertDescription>
            Coming Soon!
          </AlertDescription>
        </Alert>
      </div>
    </div>
    </>
  )
}