"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import {
  Menu,
} from 'lucide-react'

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet"
import { ThemeToggle } from "@/components/theme-toggle"

interface NavbarProps {
  fontName?: string;
}

const navItems = [
  { title: "Home", href: "/" },
  { title: "About", href: "/about" },
  { title: "Contact", href: "/contact" },
]

export function Navbar({ fontName }: NavbarProps) {
  const [isScrolled, setIsScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 0) {
        setIsScrolled(true)
      } else {
        setIsScrolled(false)
      }
    }

    window.addEventListener("scroll", handleScroll)
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  return (
    <header className={cn(
      "fixed top-0 left-0 right-0 z-50 transition-colors duration-300",
      isScrolled ? "bg-background/80 backdrop-blur-md" : "bg-transparent"
    )}>
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          <Link 
            href="/" 
            className={cn(
              "text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-red-900 drop-shadow-[0_1px_1px_rgba(0,0,0,0.1)]",
              fontName
            )}
          >
            twinyn
          </Link>
          {/* <nav className="hidden md:flex space-x-4 ml-auto">
            {navItems.map((item) => (
              <Link
                key={item.title}
                href={item.href}
                className="text-sm font-medium text-muted-foreground hover:text-primary"
              >
                {item.title}
              </Link>
            ))}
          </nav> */}
          <div>
            <ThemeToggle />
          </div>
        </div>
      </div>
    </header>
  )
}
