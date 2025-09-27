import React, { CSSProperties, memo, useCallback, useRef } from 'react';
import { FixedSizeList, VariableSizeList, ListChildComponentProps } from 'react-window';
import InfiniteLoader from 'react-window-infinite-loader';

interface VirtualizedListProps<T> {
  items: T[];
  height?: number;
  itemSize?: number | ((index: number) => number);
  renderItem: (item: T, index: number, style: CSSProperties) => React.ReactNode;
  onLoadMore?: () => Promise<void>;
  hasMore?: boolean;
  loading?: boolean;
  overscanCount?: number;
  className?: string;
}

/**
 * High-performance virtualized list component
 */
export function VirtualizedList<T>({
  items,
  height = 600,
  itemSize = 50,
  renderItem,
  onLoadMore,
  hasMore = false,
  loading = false,
  overscanCount = 5,
  className = ''
}: VirtualizedListProps<T>) {
  const listRef = useRef<FixedSizeList | VariableSizeList>(null);

  // Determine total count including potential unloaded items
  const itemCount = hasMore ? items.length + 1 : items.length;

  // Check if an item is loaded
  const isItemLoaded = useCallback(
    (index: number) => !hasMore || index < items.length,
    [hasMore, items.length]
  );

  // Load more items
  const loadMoreItems = useCallback(
    () => onLoadMore?.() || Promise.resolve(),
    [onLoadMore]
  );

  // Render individual row
  const Row = memo(({ index, style }: ListChildComponentProps) => {
    if (!isItemLoaded(index)) {
      return (
        <div style={style} className="flex items-center justify-center p-4">
          <div className="loading-spinner" />
        </div>
      );
    }

    const item = items[index];
    return <>{renderItem(item, index, style)}</>;
  });

  Row.displayName = 'VirtualizedRow';

  // Render with infinite loader if onLoadMore is provided
  if (onLoadMore) {
    return (
      <InfiniteLoader
        isItemLoaded={isItemLoaded}
        itemCount={itemCount}
        loadMoreItems={loadMoreItems}
      >
        {({ onItemsRendered, ref }) => {
          const ListComponent = typeof itemSize === 'function' ? VariableSizeList : FixedSizeList;

          return (
            <ListComponent
              ref={ref}
              className={className}
              height={height}
              itemCount={itemCount}
              itemSize={itemSize}
              onItemsRendered={onItemsRendered}
              overscanCount={overscanCount}
            >
              {Row}
            </ListComponent>
          );
        }}
      </InfiniteLoader>
    );
  }

  // Regular virtualized list without infinite loading
  const ListComponent = typeof itemSize === 'function' ? VariableSizeList : FixedSizeList;

  return (
    <ListComponent
      ref={listRef}
      className={className}
      height={height}
      itemCount={items.length}
      itemSize={itemSize}
      overscanCount={overscanCount}
    >
      {Row}
    </ListComponent>
  );
}

/**
 * Virtualized grid component for media galleries
 */
interface VirtualizedGridProps<T> {
  items: T[];
  columnCount?: number;
  height?: number;
  rowHeight?: number;
  renderItem: (item: T, index: number, style: CSSProperties) => React.ReactNode;
  gap?: number;
  className?: string;
}

export function VirtualizedGrid<T>({
  items,
  columnCount = 3,
  height = 600,
  rowHeight = 200,
  renderItem,
  gap = 16,
  className = ''
}: VirtualizedGridProps<T>) {
  const rowCount = Math.ceil(items.length / columnCount);

  const Row = memo(({ index, style }: ListChildComponentProps) => {
    const startIndex = index * columnCount;
    const endIndex = Math.min(startIndex + columnCount, items.length);
    const rowItems = items.slice(startIndex, endIndex);

    return (
      <div style={style} className="flex" >
        {rowItems.map((item, colIndex) => {
          const itemIndex = startIndex + colIndex;
          const itemStyle: CSSProperties = {
            width: `calc(${100 / columnCount}% - ${(gap * (columnCount - 1)) / columnCount}px)`,
            marginRight: colIndex < rowItems.length - 1 ? gap : 0
          };

          return (
            <div key={itemIndex} style={itemStyle}>
              {renderItem(item, itemIndex, itemStyle)}
            </div>
          );
        })}
      </div>
    );
  });

  Row.displayName = 'VirtualizedGridRow';

  return (
    <FixedSizeList
      className={className}
      height={height}
      itemCount={rowCount}
      itemSize={rowHeight + gap}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  );
}

/**
 * Auto-sizing wrapper for dynamic height lists
 */
interface AutoSizedVirtualizedListProps<T> extends Omit<VirtualizedListProps<T>, 'height'> {
  minHeight?: number;
  maxHeight?: number;
}

export function AutoSizedVirtualizedList<T>({
  minHeight = 200,
  maxHeight = 800,
  ...props
}: AutoSizedVirtualizedListProps<T>) {
  const [height, setHeight] = React.useState(minHeight);
  const containerRef = useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const updateHeight = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const availableHeight = window.innerHeight - rect.top - 20; // 20px bottom margin
        setHeight(Math.max(minHeight, Math.min(maxHeight, availableHeight)));
      }
    };

    updateHeight();

    // Update on resize
    window.addEventListener('resize', updateHeight);
    return () => window.removeEventListener('resize', updateHeight);
  }, [minHeight, maxHeight]);

  return (
    <div ref={containerRef}>
      <VirtualizedList {...props} height={height} />
    </div>
  );
}

/**
 * Hook for managing virtualized list state
 */
export function useVirtualizedList<T>(
  initialItems: T[] = [],
  loadMore?: () => Promise<T[]>
) {
  const [items, setItems] = React.useState<T[]>(initialItems);
  const [loading, setLoading] = React.useState(false);
  const [hasMore, setHasMore] = React.useState(true);

  const handleLoadMore = useCallback(async () => {
    if (loading || !loadMore) return;

    setLoading(true);
    try {
      const newItems = await loadMore();
      setItems(prev => [...prev, ...newItems]);
      setHasMore(newItems.length > 0);
    } catch (error) {
      console.error('Failed to load more items:', error);
    } finally {
      setLoading(false);
    }
  }, [loading, loadMore]);

  return {
    items,
    loading,
    hasMore,
    onLoadMore: handleLoadMore,
    setItems
  };
}
