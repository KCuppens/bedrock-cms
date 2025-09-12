import { SimpleDialog, SimpleDialogHeader, SimpleDialogTitle } from "@/components/ui/simple-dialog";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

interface DeleteConfirmModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  itemName: string;
  onConfirm: () => void;
  isDestructive?: boolean;
  warningMessage?: string;
  isLoading?: boolean;
}

const DeleteConfirmModal = ({
  open,
  onOpenChange,
  title,
  description,
  itemName,
  onConfirm,
  isDestructive = true,
  warningMessage,
  isLoading = false
}: DeleteConfirmModalProps) => {

  const handleConfirm = () => {
    onConfirm();
    // Don't close here - let the parent handle it after async operation completes
  };

  return (
    <SimpleDialog open={open} onOpenChange={onOpenChange}>
      <SimpleDialogHeader>
        <SimpleDialogTitle className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-destructive" />
          {title}
        </SimpleDialogTitle>
        <p className="text-sm text-muted-foreground mt-2">
          {description}
        </p>
      </SimpleDialogHeader>

        <div className="py-4">
          <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
            <p className="text-sm font-medium">
              You are about to delete: <span className="font-semibold">{itemName}</span>
            </p>
            {warningMessage && (
              <p className="text-sm text-muted-foreground mt-2">
                {warningMessage}
              </p>
            )}
          </div>
        </div>

        <div className="flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 pt-4">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            variant={isDestructive ? "destructive" : "default"}
            onClick={handleConfirm}
            disabled={isLoading}
            className="sm:ml-2"
          >
            {isLoading ? 'Deleting...' : (isDestructive ? 'Delete' : 'Confirm')}
          </Button>
        </div>
    </SimpleDialog>
  );
};

export default DeleteConfirmModal;
