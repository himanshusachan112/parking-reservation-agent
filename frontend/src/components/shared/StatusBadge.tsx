import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { statusColors } from "@/lib/helpers";
import type { ReservationStatus } from "@/types";

interface StatusBadgeProps {
  status: ReservationStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "font-medium capitalize",
        statusColors[status],
        className
      )}
    >
      {status}
    </Badge>
  );
}
