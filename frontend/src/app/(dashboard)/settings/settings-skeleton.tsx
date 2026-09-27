import { SettingsCard } from "@/app/(dashboard)/settings/settings-card";
import { Skeleton } from "@/components/ui/skeleton";

/** Loading placeholder shared by the settings sections. */
function SettingsSkeleton({
  title,
  description,
  rows = 4,
}: {
  title: string;
  description: string;
  rows?: number;
}) {
  return (
    <SettingsCard title={title} description={description}>
      <div className="flex flex-col gap-4">
        {Array.from({ length: rows }).map((_, index) => (
          <Skeleton key={index} className="h-9 w-full" />
        ))}
      </div>
    </SettingsCard>
  );
}

export { SettingsSkeleton };
