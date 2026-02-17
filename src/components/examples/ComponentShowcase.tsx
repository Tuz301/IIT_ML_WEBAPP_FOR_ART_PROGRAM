import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "@/hooks/use-toast"

/**
 * Component Showcase
 *
 * This component demonstrates the usage of the new shadcn/ui components
 * that were added to the project. You can use this as a reference for
 * implementing these components in your own pages.
 */
function ComponentShowcase() {
  const [inputValue, setInputValue] = useState("")
  const [selectValue, setSelectValue] = useState("")
  const [dialogOpen, setDialogOpen] = useState(false)

  const handleToast = () => {
    toast({
      title: "Success!",
      description: "This is a toast notification using the new shadcn/ui toast component.",
    })
  }

  const handleDialogSubmit = () => {
    toast({
      title: "Dialog Submitted",
      description: `You entered: ${inputValue}`,
    })
    setDialogOpen(false)
  }

  return (
    <div className="container mx-auto p-6 space-y-8">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">shadcn/ui Component Showcase</h1>
        <p className="text-muted-foreground">
          Demonstrating the new components added to the project
        </p>
      </div>

      {/* Button Variants */}
      <Card>
        <CardHeader>
          <CardTitle>Button Variants</CardTitle>
          <CardDescription>
            Different button styles for different use cases
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button variant="default">Default</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="link">Link</Button>
          <Button variant="destructive">Destructive</Button>
        </CardContent>
      </Card>

      {/* Button Sizes */}
      <Card>
        <CardHeader>
          <CardTitle>Button Sizes</CardTitle>
          <CardDescription>
            Different button sizes for different contexts
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-2">
          <Button size="sm">Small</Button>
          <Button size="default">Default</Button>
          <Button size="lg">Large</Button>
          <Button size="icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14"/>
              <path d="m12 5 7 7-7 7"/>
            </svg>
          </Button>
        </CardContent>
      </Card>

      {/* Form Components */}
      <Card>
        <CardHeader>
          <CardTitle>Form Components</CardTitle>
          <CardDescription>
            Input, Label, and Select components working together
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="input">Email Input</Label>
            <Input
              id="input"
              type="email"
              placeholder="Enter your email"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="select">Select Dropdown</Label>
            <Select value={selectValue} onValueChange={setSelectValue}>
              <SelectTrigger id="select">
                <SelectValue placeholder="Select an option" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="option1">Option 1</SelectItem>
                <SelectItem value="option2">Option 2</SelectItem>
                <SelectItem value="option3">Option 3</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Dialog Component */}
      <Card>
        <CardHeader>
          <CardTitle>Dialog Component</CardTitle>
          <CardDescription>
            Modal dialog for important interactions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>Open Dialog</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Are you sure?</DialogTitle>
                <DialogDescription>
                  This action cannot be undone. This will permanently delete your account and remove your data from our servers.
                </DialogDescription>
              </DialogHeader>
              <div className="py-4">
                <p className="text-sm text-muted-foreground">
                  Current input value: <strong>{inputValue || "(empty)"}</strong>
                </p>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleDialogSubmit}>Confirm</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>

      {/* Toast Component */}
      <Card>
        <CardHeader>
          <CardTitle>Toast Notifications</CardTitle>
          <CardDescription>
            Click the button to show a toast notification
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={handleToast}>Show Toast</Button>
        </CardContent>
      </Card>

      {/* Card Examples */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Card Title 1</CardTitle>
            <CardDescription>Card description goes here</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              This is the content area of the card. You can put any content here.
            </p>
          </CardContent>
          <CardFooter>
            <Button variant="outline" className="w-full">View Details</Button>
          </CardFooter>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Card Title 2</CardTitle>
            <CardDescription>Another card description</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Cards are great for grouping related content and actions together.
            </p>
          </CardContent>
          <CardFooter className="flex gap-2">
            <Button variant="outline" className="flex-1">Cancel</Button>
            <Button className="flex-1">Confirm</Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}

export default ComponentShowcase
