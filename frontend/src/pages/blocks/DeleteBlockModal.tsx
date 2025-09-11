import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

interface BlockType {
  id: number;
  label: string;
}

interface DeleteBlockModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => Promise<void>;
  blockType: BlockType | null;
}

export default function DeleteBlockModal({ 
  open, 
  onOpenChange, 
  onConfirm,
  blockType 
}: DeleteBlockModalProps) {
  if (!blockType) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Block Type</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete "{blockType.label}"? This will deactivate the block type and make it unavailable in the editor.
          </DialogDescription>
        </DialogHeader>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={onConfirm}>
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}