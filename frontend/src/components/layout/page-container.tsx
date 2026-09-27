import * as React from "react";

import { cn } from "@/lib/utils";

/** Page-level content container: consistent gutters and max reading width. */
function PageContainer({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="page-container"
      className={cn(
        "mx-auto flex w-full max-w-[1440px] flex-1 flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8 lg:py-8",
        className,
      )}
      {...props}
    />
  );
}

export { PageContainer };
