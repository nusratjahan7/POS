"use client";

import { DateField, DateRangePicker, RangeCalendar } from "@heroui/react";
import type { DateValue } from "@internationalized/date";
import { X } from "lucide-react";

export type PickedDateRange = {
  start: DateValue;
  end: DateValue;
};

/**
 * The toolbar's date-range filter, built on HeroUI's `RangeCalendar`.
 *
 * `DateRangePicker` supplies the trigger field and popover; the calendar itself
 * is the composition from the HeroUI docs. Values are `CalendarDate`s, so the
 * caller serialises them to `YYYY-MM-DD` for the API.
 */
export function SalesDateRange({
  value,
  onChange,
}: {
  value: PickedDateRange | null;
  onChange: (range: PickedDateRange | null) => void;
}) {
  return (
    <DateRangePicker
      aria-label="Filter sales by date range"
      value={value}
      onChange={onChange}
      className="w-full sm:w-64"
    >
      <DateField.Group>
        <DateField.InputContainer>
          <DateField.Input slot="start">
            {(segment) => <DateField.Segment segment={segment} />}
          </DateField.Input>
          <DateRangePicker.RangeSeparator />
          <DateField.Input slot="end">
            {(segment) => <DateField.Segment segment={segment} />}
          </DateField.Input>
        </DateField.InputContainer>
        <DateField.Suffix>
          {/* Only offered once a range is set, so the field stays quiet when empty. */}
          {value ? (
            <button
              type="button"
              onClick={() => onChange(null)}
              aria-label="Clear date range"
              className="text-muted-foreground hover:text-foreground focus-visible:ring-ring/50 me-1 inline-flex size-5 items-center justify-center rounded-sm outline-none transition-colors focus-visible:ring-2"
            >
              <X className="size-3.5" aria-hidden />
            </button>
          ) : null}
          <DateRangePicker.Trigger>
            <DateRangePicker.TriggerIndicator />
          </DateRangePicker.Trigger>
        </DateField.Suffix>
      </DateField.Group>
      <DateRangePicker.Popover>
        <RangeCalendar aria-label="Sale dates" firstDayOfWeek="mon">
          <RangeCalendar.Header>
            <RangeCalendar.Heading />
            <RangeCalendar.NavButton slot="previous" />
            <RangeCalendar.NavButton slot="next" />
          </RangeCalendar.Header>
          <RangeCalendar.Grid>
            <RangeCalendar.GridHeader>
              {(day) => <RangeCalendar.HeaderCell>{day}</RangeCalendar.HeaderCell>}
            </RangeCalendar.GridHeader>
            <RangeCalendar.GridBody>
              {(date) => <RangeCalendar.Cell date={date} />}
            </RangeCalendar.GridBody>
          </RangeCalendar.Grid>
        </RangeCalendar>
      </DateRangePicker.Popover>
    </DateRangePicker>
  );
}
