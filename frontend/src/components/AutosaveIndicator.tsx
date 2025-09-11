import React from 'react';
import { format } from 'date-fns';
import { CheckCircle, Clock, AlertTriangle, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { AutosaveState } from '@/hooks/useAutosave';

interface AutosaveIndicatorProps {
  autosaveState: AutosaveState;
  className?: string;
}

const AutosaveIndicator: React.FC<AutosaveIndicatorProps> = ({
  autosaveState,
  className
}) => {
  const getStatusIcon = () => {
    switch (autosaveState.status) {
      case 'saving':
        return <Loader2 className="w-3 h-3 animate-spin" />;
      case 'saved':
        return <CheckCircle className="w-3 h-3 text-green-600" />;
      case 'error':
        return <AlertTriangle className="w-3 h-3 text-red-600" />;
      default:
        return <Clock className="w-3 h-3 text-gray-600" />;
    }
  };

  const getStatusText = () => {
    switch (autosaveState.status) {
      case 'saving':
        return 'Saving...';
      case 'saved':
        return autosaveState.lastSaved 
          ? `Saved ${format(autosaveState.lastSaved, 'h:mm a')}`
          : 'Saved';
      case 'error':
        return 'Save failed';
      default:
        return autosaveState.hasUnsavedChanges ? 'Unsaved changes' : 'Up to date';
    }
  };

  const getVariant = () => {
    switch (autosaveState.status) {
      case 'saved':
        return 'default';
      case 'error':
        return 'destructive';
      case 'saving':
        return 'secondary';
      default:
        return autosaveState.hasUnsavedChanges ? 'outline' : 'secondary';
    }
  };

  return (
    <Badge 
      variant={getVariant()} 
      className={`flex items-center gap-1 ${className}`}
      title={autosaveState.error || getStatusText()}
    >
      {getStatusIcon()}
      <span className="text-xs">{getStatusText()}</span>
    </Badge>
  );
};

export default AutosaveIndicator;
