import { memo } from "react";
import KeyboardShortcutsHelp from "@/components/KeyboardShortcutsHelp";
import { GlobalSearchBar } from "@/components/GlobalSearchBar";
import SimpleLanguageSelector from "@/components/SimpleLanguageSelector";

const TopNavbar = memo(() => {
  return (
    <div className="border-b border-border/20">
      <div className="flex items-center justify-between px-6 py-3">

        {/* Global Search Bar */}
        <GlobalSearchBar />

        {/* Language Selector and Shortcuts */}
        <div className="flex items-center gap-3">
          <SimpleLanguageSelector />
          <KeyboardShortcutsHelp />
        </div>
      </div>
    </div>
  );
});

TopNavbar.displayName = 'TopNavbar';

export default TopNavbar;