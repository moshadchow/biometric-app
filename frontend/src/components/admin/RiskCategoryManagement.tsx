import React from "react";
import {
  createRiskBusinessCategory,
  createRiskProfessionCategory,
  getRiskBusinessCategoryAudit,
  getRiskProfessionCategoryAudit,
  listRiskBusinessCategories,
  listRiskProfessionCategories,
  setRiskBusinessCategoryActive,
  setRiskProfessionCategoryActive,
  updateRiskBusinessCategory,
  updateRiskProfessionCategory,
} from "@/api/ComplianceApi";
import type {
  AuditLogEntry,
  RiskBusinessCategory,
  RiskBusinessCategoryPayload,
  RiskProfessionCategory,
  RiskProfessionCategoryPayload,
} from "@/types";

type CategoryKind = "business" | "profession";
type CategoryRow = RiskBusinessCategory | RiskProfessionCategory;

interface CategoryFormState {
  code: string;
  name: string;
  score: string;
  description: string;
  active: boolean;
  reason: string;
}

const emptyForm: CategoryFormState = {
  code: "",
  name: "",
  score: "3",
  description: "",
  active: true,
  reason: "Updated from admin portal.",
};

export const RiskCategoryManagement: React.FC<{ kind: CategoryKind }> = ({ kind }) => {
  const [items, setItems] = React.useState<CategoryRow[]>([]);
  const [selected, setSelected] = React.useState<CategoryRow | null>(null);
  const [audit, setAudit] = React.useState<AuditLogEntry[]>([]);
  const [query, setQuery] = React.useState("");
  const [activeFilter, setActiveFilter] = React.useState<"all" | "active" | "inactive">("all");
  const [form, setForm] = React.useState<CategoryFormState>(emptyForm);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState("");

  const title = kind === "business" ? "Risk Business Categories" : "Risk Profession Categories";
  const codeLabel = kind === "business" ? "Category Code" : "Profession Code";
  const nameLabel = kind === "business" ? "Category Name" : "Profession Name";

  const loadItems = React.useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = {
        q: query || undefined,
        is_active: activeFilter === "all" ? undefined : activeFilter === "active",
      };
      const response =
        kind === "business"
          ? await listRiskBusinessCategories(params)
          : await listRiskProfessionCategories(params);
      setItems(response.items);
      setSelected((current) => {
        if (!current) {
          return response.items[0] ?? null;
        }
        return response.items.find((item) => item.id === current.id) ?? response.items[0] ?? null;
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : String(loadError));
    } finally {
      setLoading(false);
    }
  }, [activeFilter, kind, query]);

  React.useEffect(() => {
    void loadItems();
  }, [loadItems]);

  React.useEffect(() => {
    if (!selected) {
      setAudit([]);
      setForm(emptyForm);
      return;
    }
    const code = "category_code" in selected ? selected.category_code : selected.profession_code;
    const name = "category_name" in selected ? selected.category_name : selected.profession_name;
    setForm({
      code,
      name,
      score: String(selected.risk_score),
      description: selected.description ?? "",
      active: selected.is_active,
      reason: "Updated from admin portal.",
    });
    let cancelled = false;
    void (async () => {
      try {
        const entries =
          kind === "business"
            ? await getRiskBusinessCategoryAudit(selected.id)
            : await getRiskProfessionCategoryAudit(selected.id);
        if (!cancelled) {
          setAudit(entries);
        }
      } catch (auditError) {
        if (!cancelled) {
          setError(auditError instanceof Error ? auditError.message : String(auditError));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [kind, selected]);

  const save = React.useCallback(
    async (mode: "create" | "update") => {
      setSaving(true);
      setError("");
      try {
        const score = Number(form.score);
        if (!Number.isFinite(score) || score < 0) {
          throw new Error("Risk score must be a valid positive number.");
        }
        if (kind === "business") {
          const payload: RiskBusinessCategoryPayload = {
            category_code: form.code,
            category_name: form.name,
            risk_score: score,
            description: form.description || null,
            is_active: form.active,
            reason: form.reason,
          };
          if (mode === "create") {
            await createRiskBusinessCategory(payload);
          } else if (selected) {
            await updateRiskBusinessCategory(selected.id, payload);
          }
        } else {
          const payload: RiskProfessionCategoryPayload = {
            profession_code: form.code,
            profession_name: form.name,
            risk_score: score,
            description: form.description || null,
            is_active: form.active,
            reason: form.reason,
          };
          if (mode === "create") {
            await createRiskProfessionCategory(payload);
          } else if (selected) {
            await updateRiskProfessionCategory(selected.id, payload);
          }
        }
        await loadItems();
      } catch (saveError) {
        setError(saveError instanceof Error ? saveError.message : String(saveError));
      } finally {
        setSaving(false);
      }
    },
    [form, kind, loadItems, selected]
  );

  const toggleActive = React.useCallback(async () => {
    if (!selected) {
      return;
    }
    setSaving(true);
    setError("");
    try {
      if (kind === "business") {
        await setRiskBusinessCategoryActive(selected.id, !selected.is_active, form.reason);
      } else {
        await setRiskProfessionCategoryActive(selected.id, !selected.is_active, form.reason);
      }
      await loadItems();
    } catch (toggleError) {
      setError(toggleError instanceof Error ? toggleError.message : String(toggleError));
    } finally {
      setSaving(false);
    }
  }, [form.reason, kind, loadItems, selected]);

  return (
    <div style={s.panel}>
      <div style={s.panelHeader}>
        <div>
          <div style={s.panelTitle}>{title}</div>
          <div style={s.panelMeta}>Maintain scores used by subsequent customer risk assessments.</div>
        </div>
        <div style={s.filterRow}>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search"
            style={s.input}
          />
          <select value={activeFilter} onChange={(event) => setActiveFilter(event.target.value as typeof activeFilter)} style={s.select}>
            <option value="all">All</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </div>

      {error && <div style={s.errorBanner}>{error}</div>}

      <div style={s.grid}>
        <div style={s.list}>
          {loading ? (
            <div style={s.emptyState}>Loading categories...</div>
          ) : items.length === 0 ? (
            <div style={s.emptyState}>No categories match the current filter.</div>
          ) : (
            items.map((item) => {
              const code = "category_code" in item ? item.category_code : item.profession_code;
              const name = "category_name" in item ? item.category_name : item.profession_name;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelected(item)}
                  style={{
                    ...s.rowButton,
                    ...(selected?.id === item.id ? s.rowButtonActive : {}),
                  }}
                >
                  <span>
                    <span style={s.rowTitle}>{name}</span>
                    <span style={s.rowMeta}>{code}</span>
                  </span>
                  <span style={s.scoreBadge}>{item.risk_score}</span>
                </button>
              );
            })
          )}
        </div>

        <div style={s.editor}>
          <div style={s.formGrid}>
            <label style={s.label}>
              {codeLabel}
              <input value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} style={s.input} />
            </label>
            <label style={s.label}>
              {nameLabel}
              <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} style={s.input} />
            </label>
            <label style={s.label}>
              Risk Score
              <input value={form.score} onChange={(event) => setForm({ ...form, score: event.target.value })} style={s.input} type="number" min="0" />
            </label>
            <label style={s.checkboxLabel}>
              <input checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })} type="checkbox" />
              Active
            </label>
            <label style={s.labelWide}>
              Description
              <textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} style={s.textarea} />
            </label>
            <label style={s.labelWide}>
              Change Reason
              <input value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} style={s.input} />
            </label>
          </div>

          {selected && (
            <div style={s.summaryRow}>
              <span>{selected.is_active ? "Active" : "Inactive"}</span>
              <span>{selected.usage_count} assessment uses</span>
              <span>Updated {new Date(selected.updated_at).toLocaleDateString()}</span>
            </div>
          )}

          <div style={s.actionRow}>
            <button type="button" style={s.primaryButton} disabled={saving} onClick={() => void save("create")}>
              Create
            </button>
            <button type="button" style={s.secondaryButton} disabled={saving || !selected} onClick={() => void save("update")}>
              Save
            </button>
            <button type="button" style={s.dangerButton} disabled={saving || !selected} onClick={() => void toggleActive()}>
              {selected?.is_active ? "Deactivate" : "Activate"}
            </button>
          </div>

          <section style={s.auditPanel}>
            <div style={s.auditTitle}>Audit History</div>
            {audit.length === 0 ? (
              <div style={s.emptyState}>No audit entries for this category.</div>
            ) : (
              audit.map((entry) => (
                <div key={entry.id} style={s.auditEntry}>
                  <div style={s.rowTitle}>{entry.event_type}</div>
                  <div style={s.rowMeta}>{entry.message}</div>
                  <div style={s.rowMeta}>{new Date(entry.created_at).toLocaleString()}</div>
                </div>
              ))
            )}
          </section>
        </div>
      </div>
    </div>
  );
};

const s: Record<string, React.CSSProperties> = {
  panel: {
    borderRadius: 20,
    border: "1px solid #1f1f1f",
    background: "rgba(10,10,10,0.96)",
    padding: "1rem",
    display: "grid",
    gap: "1rem",
  },
  panelHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: "1rem",
    flexWrap: "wrap",
  },
  panelTitle: {
    color: "#f4f4f4",
    fontWeight: 800,
    fontSize: "1.1rem",
  },
  panelMeta: {
    color: "#a1a1a1",
    marginTop: 4,
  },
  filterRow: {
    display: "flex",
    gap: "0.6rem",
    alignItems: "center",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "minmax(260px, 360px) minmax(0, 1fr)",
    gap: "1rem",
  },
  list: {
    display: "grid",
    gap: "0.55rem",
    alignContent: "start",
  },
  rowButton: {
    width: "100%",
    minHeight: 72,
    borderRadius: 14,
    border: "1px solid #262626",
    background: "#111",
    color: "#f4f4f4",
    padding: "0.8rem",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "0.8rem",
    textAlign: "left",
    cursor: "pointer",
  },
  rowButtonActive: {
    borderColor: "#38b6ff",
    background: "rgba(56, 182, 255, 0.08)",
  },
  rowTitle: {
    display: "block",
    color: "#f4f4f4",
    fontWeight: 700,
  },
  rowMeta: {
    display: "block",
    color: "#a1a1a1",
    fontSize: "0.82rem",
    marginTop: 4,
  },
  scoreBadge: {
    minWidth: 40,
    minHeight: 40,
    borderRadius: 20,
    background: "#38b6ff",
    color: "#061017",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 800,
  },
  editor: {
    display: "grid",
    gap: "1rem",
    alignContent: "start",
  },
  formGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
    gap: "0.8rem",
  },
  label: {
    color: "#d8d8d8",
    fontWeight: 700,
    display: "grid",
    gap: 6,
  },
  labelWide: {
    color: "#d8d8d8",
    fontWeight: 700,
    display: "grid",
    gap: 6,
    gridColumn: "1 / -1",
  },
  checkboxLabel: {
    color: "#d8d8d8",
    fontWeight: 700,
    display: "flex",
    gap: "0.5rem",
    alignItems: "center",
  },
  input: {
    minHeight: 42,
    borderRadius: 12,
    border: "1px solid #333",
    background: "#0b0b0b",
    color: "#f4f4f4",
    padding: "0.65rem 0.75rem",
  },
  select: {
    minHeight: 42,
    borderRadius: 12,
    border: "1px solid #333",
    background: "#0b0b0b",
    color: "#f4f4f4",
    padding: "0.65rem 0.75rem",
  },
  textarea: {
    minHeight: 92,
    borderRadius: 12,
    border: "1px solid #333",
    background: "#0b0b0b",
    color: "#f4f4f4",
    padding: "0.65rem 0.75rem",
    resize: "vertical",
  },
  summaryRow: {
    display: "flex",
    gap: "0.8rem",
    flexWrap: "wrap",
    color: "#a1a1a1",
    fontSize: "0.9rem",
  },
  actionRow: {
    display: "flex",
    gap: "0.7rem",
    flexWrap: "wrap",
  },
  primaryButton: {
    borderRadius: 12,
    border: "1px solid #38b6ff",
    background: "#38b6ff",
    color: "#061017",
    padding: "0.75rem 1rem",
    fontWeight: 800,
    cursor: "pointer",
  },
  secondaryButton: {
    borderRadius: 12,
    border: "1px solid rgba(255, 255, 255, 0.18)",
    background: "rgba(255, 255, 255, 0.05)",
    color: "#f4f4f4",
    padding: "0.75rem 1rem",
    fontWeight: 800,
    cursor: "pointer",
  },
  dangerButton: {
    borderRadius: 12,
    border: "1px solid rgba(255, 100, 100, 0.55)",
    background: "rgba(255, 100, 100, 0.12)",
    color: "#ffb4b4",
    padding: "0.75rem 1rem",
    fontWeight: 800,
    cursor: "pointer",
  },
  auditPanel: {
    display: "grid",
    gap: "0.6rem",
  },
  auditTitle: {
    color: "#f4f4f4",
    fontWeight: 800,
  },
  auditEntry: {
    borderRadius: 12,
    border: "1px solid #262626",
    padding: "0.75rem",
    background: "#111",
  },
  errorBanner: {
    borderRadius: 12,
    border: "1px solid rgba(255, 100, 100, 0.45)",
    background: "rgba(255, 100, 100, 0.1)",
    color: "#ffb4b4",
    padding: "0.85rem",
  },
  emptyState: {
    color: "#a1a1a1",
    padding: "0.8rem 0",
  },
};
