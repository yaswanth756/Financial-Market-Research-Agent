'use client';

import { useState } from 'react';
import Sidebar from "./components/Sidebar";
import ChatInterface from "./components/ChatInterface";

export default function Home() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-black text-white selection:bg-zinc-800 selection:text-white">
      <Sidebar isOpen={isSidebarOpen} />
      <ChatInterface
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
      />
    </div>
  );
}
