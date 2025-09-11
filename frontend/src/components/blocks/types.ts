export interface BlockComponentProps {
  content: Record<string, any>;
  isEditing?: boolean;
  isSelected?: boolean;
  onChange?: (content: Record<string, any>) => void;
  onSelect?: () => void;
  className?: string;
}

export interface BlockConfig {
  type: string;
  label: string;
  category: string;
  icon: string;
  description?: string;
  defaultProps: Record<string, any>;
  preload?: boolean;
  editingMode?: 'inline' | 'modal' | 'sidebar';
}

export interface BlockType {
  type: string;
  label: string;
  component: string;
  category: string;
  icon: string;
  description: string;
  defaultProps: Record<string, any>;
}

export interface BlockData {
  type: string;
  component?: string;
  props: Record<string, any>;
  id?: string;
  position?: number;
}