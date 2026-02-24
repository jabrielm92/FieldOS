import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
import { Checkbox } from "../../components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";

/**
 * CustomFieldRenderer
 *
 * Renders a list of dynamic custom fields based on their type definitions.
 *
 * Props:
 *   fields   - Array of field definition objects from the tenant's custom_fields
 *   values   - Object mapping field slugs to their current values
 *   onChange - Callback (slug, value) => void called when a field value changes
 */
export default function CustomFieldRenderer({ fields = [], values = {}, onChange }) {
  if (!fields || fields.length === 0) return null;

  const handleChange = (slug, value) => {
    if (typeof onChange === "function") {
      onChange(slug, value);
    }
  };

  return (
    <div className="space-y-4">
      {fields.map((field) => {
        const slug = field.slug || field.name?.toLowerCase().replace(/\s+/g, "_");
        const value = values[slug];
        const labelText = (
          <span>
            {field.name}
            {field.required && (
              <span className="text-destructive ml-1" aria-label="required">
                *
              </span>
            )}
          </span>
        );

        switch (field.type) {
          case "NUMBER":
            return (
              <div key={field.id || slug} className="space-y-2">
                <Label>{labelText}</Label>
                <Input
                  type="number"
                  value={value ?? ""}
                  onChange={(e) =>
                    handleChange(slug, e.target.value === "" ? "" : Number(e.target.value))
                  }
                  required={field.required}
                />
              </div>
            );

          case "SELECT":
            return (
              <div key={field.id || slug} className="space-y-2">
                <Label>{labelText}</Label>
                <Select
                  value={value ?? ""}
                  onValueChange={(v) => handleChange(slug, v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select an option" />
                  </SelectTrigger>
                  <SelectContent>
                    {(field.options || []).map((opt) => (
                      <SelectItem key={opt} value={opt}>
                        {opt}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            );

          case "MULTISELECT": {
            const selected = Array.isArray(value) ? value : [];
            return (
              <div key={field.id || slug} className="space-y-2">
                <Label>{labelText}</Label>
                <div className="flex flex-wrap gap-3">
                  {(field.options || []).map((opt) => (
                    <div key={opt} className="flex items-center gap-2">
                      <Checkbox
                        id={`${slug}-${opt}`}
                        checked={selected.includes(opt)}
                        onCheckedChange={(checked) => {
                          const next = checked
                            ? [...selected, opt]
                            : selected.filter((v) => v !== opt);
                          handleChange(slug, next);
                        }}
                      />
                      <label
                        htmlFor={`${slug}-${opt}`}
                        className="text-sm cursor-pointer"
                      >
                        {opt}
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            );
          }

          case "DATE":
            return (
              <div key={field.id || slug} className="space-y-2">
                <Label>{labelText}</Label>
                <Input
                  type="date"
                  value={value ?? ""}
                  onChange={(e) => handleChange(slug, e.target.value)}
                  required={field.required}
                />
              </div>
            );

          case "BOOLEAN":
            return (
              <div key={field.id || slug} className="flex items-center justify-between">
                <Label>{labelText}</Label>
                <Switch
                  checked={Boolean(value)}
                  onCheckedChange={(checked) => handleChange(slug, checked)}
                />
              </div>
            );

          // Default: TEXT
          default:
            return (
              <div key={field.id || slug} className="space-y-2">
                <Label>{labelText}</Label>
                <Input
                  type="text"
                  value={value ?? ""}
                  onChange={(e) => handleChange(slug, e.target.value)}
                  required={field.required}
                />
              </div>
            );
        }
      })}
    </div>
  );
}
