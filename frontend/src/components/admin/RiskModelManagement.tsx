import React from "react";
import {
  activateRiskRuleVersion,
  cloneRiskRuleVersion,
  listRiskFactorRules,
  listRiskProductRisks,
  listRiskRuleVersions,
  listRiskThresholds,
  listRiskTransactionRanges,
  updateRiskFactorRule,
  updateRiskProductRisk,
  updateRiskThreshold,
  updateRiskTransactionRange,
} from "@/api/ComplianceApi";
import type {
  RiskFactorDefinition,
  RiskFactorRule,
  RiskProductCategory,
  RiskRuleVersion,
  RiskThresholdBand,
  RiskTransactionRange,
} from "@/types";

type RiskModelTab = "versions" | "rules" | "thresholds" | "transactions" | "products";

export const RiskModelManagement: React.FC = () => {
  const [tab, setTab] = React.useState<RiskModelTab>("versions");
  const [versions, setVersions] = React.useState<RiskRuleVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = React.useState<number | undefined>();
  const [definitions, setDefinitions] = React.useState<RiskFactorDefinition[]>([]);
  const [rules, setRules] = React.useState<RiskFactorRule[]>([]);
  const [thresholds, setThresholds] = React.useState<RiskThresholdBand[]>([]);
  const [transactions, setTransactions] = React.useState<RiskTransactionRange[]>([]);
  const [products, setProducts] = React.useState<RiskProductCategory[]>([]);
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [reason, setReason] = React.useState("Risk model updated from admin portal.");
  const [cloneVersion, setCloneVersion] = React.useState("");

  const loadAll = React.useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const loadedVersions = await listRiskRuleVersions();
      setVersions(loadedVersions);
      const selected = selectedVersionId ?? loadedVersions.find((item) => item.status === "ACTIVE")?.id ?? loadedVersions[0]?.id;
      setSelectedVersionId(selected);
      const [factorResponse, thresholdRows, transactionRows, productRows] = await Promise.all([
        listRiskFactorRules(selected),
        listRiskThresholds(selected),
        listRiskTransactionRanges(selected),
        listRiskProductRisks(selected),
      ]);
      setDefinitions(factorResponse.definitions);
      setRules(factorResponse.rules);
      setThresholds(thresholdRows);
      setTransactions(transactionRows);
      setProducts(productRows);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : String(loadError));
    } finally {
      setLoading(false);
    }
  }, [selectedVersionId]);

  React.useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const saveRule = async (rule: RiskFactorRule, score: number, active: boolean) => {
    await updateRiskFactorRule(rule.id, {
      factor_definition_id: rule.factor_definition_id,
      rule_code: rule.rule_code,
      rule_type: rule.rule_type,
      match_value: rule.match_value,
      min_value: rule.min_value,
      max_value: rule.max_value,
      boolean_value: rule.boolean_value,
      risk_score: score,
      description: rule.description,
      is_active: active,
      reason,
    });
    await loadAll();
  };

  const saveThreshold = async (band: RiskThresholdBand, minScore: number, maxScore: number | null, active: boolean) => {
    await updateRiskThreshold(band.id, {
      category_code: band.category_code,
      category_name: band.category_name,
      min_score: minScore,
      max_score: maxScore,
      is_active: active,
      reason,
    });
    await loadAll();
  };

  const saveTransaction = async (range: RiskTransactionRange, score: number, active: boolean) => {
    await updateRiskTransactionRange(range.id, {
      range_code: range.range_code,
      range_name: range.range_name,
      min_amount: range.min_amount,
      max_amount: range.max_amount,
      risk_score: score,
      is_active: active,
      reason,
    });
    await loadAll();
  };

  const saveProduct = async (product: RiskProductCategory, score: number, active: boolean) => {
    await updateRiskProductRisk(product.id, {
      product_code: product.product_code,
      product_name: product.product_name,
      product_category: product.product_category,
      risk_score: score,
      is_active: active,
      reason,
    });
    await loadAll();
  };

  const activeVersion = versions.find((item) => item.status === "ACTIVE");

  return (
    <div style={s.panel}>
      <div style={s.header}>
        <div>
          <div style={s.title}>Risk Management</div>
          <div style={s.meta}>Active version: {activeVersion?.version ?? "Not available"}</div>
        </div>
        <select
          value={selectedVersionId ?? ""}
          onChange={(event) => setSelectedVersionId(Number(event.target.value))}
          style={s.input}
        >
          {versions.map((version) => (
            <option key={version.id} value={version.id}>
              {version.version} - {version.status}
            </option>
          ))}
        </select>
      </div>

      <div style={s.tabBar}>
        {(["versions", "rules", "thresholds", "transactions", "products"] as RiskModelTab[]).map((item) => (
          <button key={item} type="button" onClick={() => setTab(item)} style={{ ...s.tabButton, ...(tab === item ? s.tabActive : {}) }}>
            {item.replace(/^\w/, (letter) => letter.toUpperCase())}
          </button>
        ))}
      </div>

      <label style={s.label}>
        Change Reason
        <input value={reason} onChange={(event) => setReason(event.target.value)} style={s.input} />
      </label>

      {error && <div style={s.error}>{error}</div>}
      {loading && <div style={s.empty}>Loading risk model...</div>}

      {tab === "versions" && (
        <div style={s.grid}>
          <div style={s.card}>
            <div style={s.titleSmall}>Clone Active Version</div>
            <input value={cloneVersion} onChange={(event) => setCloneVersion(event.target.value)} placeholder="v2" style={s.input} />
            <button
              type="button"
              style={s.primaryButton}
              onClick={() => void cloneRiskRuleVersion({ version: cloneVersion, change_notes: reason }).then(loadAll).catch((err) => setError(String(err)))}
            >
              Clone
            </button>
          </div>
          {versions.map((version) => (
            <div key={version.id} style={s.card}>
              <div style={s.rowTitle}>{version.version}</div>
              <div style={s.meta}>{version.status}</div>
              <div style={s.meta}>{version.change_notes ?? "No notes"}</div>
              <button
                type="button"
                style={s.secondaryButton}
                disabled={version.status === "ACTIVE"}
                onClick={() => void activateRiskRuleVersion(version.id, reason).then(loadAll).catch((err) => setError(String(err)))}
              >
                Activate
              </button>
            </div>
          ))}
        </div>
      )}

      {tab === "rules" && (
        <div style={s.list}>
          {rules.map((rule) => {
            const definition = definitions.find((item) => item.id === rule.factor_definition_id);
            return (
              <EditableScoreRow
                key={rule.id}
                title={`${definition?.factor_name ?? "Factor"} / ${rule.rule_code}`}
                meta={`${rule.rule_type} ${rule.match_value ?? ""}`}
                score={rule.risk_score}
                active={rule.is_active}
                onSave={(score, active) => saveRule(rule, score, active)}
              />
            );
          })}
        </div>
      )}

      {tab === "thresholds" && (
        <div style={s.list}>
          {thresholds.map((band) => (
            <ThresholdRow key={band.id} band={band} onSave={saveThreshold} />
          ))}
        </div>
      )}

      {tab === "transactions" && (
        <div style={s.list}>
          {transactions.map((range) => (
            <EditableScoreRow key={range.id} title={range.range_name} meta={`${range.min_amount ?? 0} - ${range.max_amount ?? "above"}`} score={range.risk_score} active={range.is_active} onSave={(score, active) => saveTransaction(range, score, active)} />
          ))}
        </div>
      )}

      {tab === "products" && (
        <div style={s.list}>
          {products.map((product) => (
            <EditableScoreRow key={product.id} title={product.product_name} meta={product.product_category} score={product.risk_score} active={product.is_active} onSave={(score, active) => saveProduct(product, score, active)} />
          ))}
        </div>
      )}
    </div>
  );
};

const EditableScoreRow: React.FC<{
  title: string;
  meta: string;
  score: number;
  active: boolean;
  onSave: (score: number, active: boolean) => Promise<void>;
}> = ({ title, meta, score, active, onSave }) => {
  const [draftScore, setDraftScore] = React.useState(String(score));
  const [draftActive, setDraftActive] = React.useState(active);
  React.useEffect(() => {
    setDraftScore(String(score));
    setDraftActive(active);
  }, [active, score]);
  return (
    <div style={s.row}>
      <div>
        <div style={s.rowTitle}>{title}</div>
        <div style={s.meta}>{meta}</div>
      </div>
      <input value={draftScore} onChange={(event) => setDraftScore(event.target.value)} type="number" style={s.smallInput} />
      <label style={s.checkLabel}>
        <input checked={draftActive} onChange={(event) => setDraftActive(event.target.checked)} type="checkbox" />
        Active
      </label>
      <button type="button" style={s.secondaryButton} onClick={() => void onSave(Number(draftScore), draftActive)}>
        Save
      </button>
    </div>
  );
};

const ThresholdRow: React.FC<{
  band: RiskThresholdBand;
  onSave: (band: RiskThresholdBand, minScore: number, maxScore: number | null, active: boolean) => Promise<void>;
}> = ({ band, onSave }) => {
  const [minScore, setMinScore] = React.useState(String(band.min_score));
  const [maxScore, setMaxScore] = React.useState(band.max_score === null || typeof band.max_score === "undefined" ? "" : String(band.max_score));
  const [active, setActive] = React.useState(band.is_active);
  return (
    <div style={s.row}>
      <div>
        <div style={s.rowTitle}>{band.category_name}</div>
        <div style={s.meta}>{band.category_code}</div>
      </div>
      <input value={minScore} onChange={(event) => setMinScore(event.target.value)} type="number" style={s.smallInput} />
      <input value={maxScore} onChange={(event) => setMaxScore(event.target.value)} placeholder="No max" type="number" style={s.smallInput} />
      <label style={s.checkLabel}>
        <input checked={active} onChange={(event) => setActive(event.target.checked)} type="checkbox" />
        Active
      </label>
      <button type="button" style={s.secondaryButton} onClick={() => void onSave(band, Number(minScore), maxScore ? Number(maxScore) : null, active)}>
        Save
      </button>
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
  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: "1rem",
    flexWrap: "wrap",
  },
  title: { color: "#f4f4f4", fontWeight: 800, fontSize: "1.1rem" },
  titleSmall: { color: "#f4f4f4", fontWeight: 800 },
  rowTitle: { color: "#f4f4f4", fontWeight: 700 },
  meta: { color: "#a1a1a1", fontSize: "0.86rem", marginTop: 4 },
  tabBar: { display: "flex", gap: "0.6rem", flexWrap: "wrap" },
  tabButton: { borderRadius: 12, border: "1px solid #333", background: "#111", color: "#d8d8d8", padding: "0.65rem 0.85rem", fontWeight: 700, cursor: "pointer" },
  tabActive: { borderColor: "#38b6ff", background: "rgba(56,182,255,0.1)", color: "#f4f4f4" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "0.75rem" },
  card: { borderRadius: 14, border: "1px solid #262626", background: "#111", padding: "0.85rem", display: "grid", gap: "0.65rem" },
  list: { display: "grid", gap: "0.6rem" },
  row: { borderRadius: 14, border: "1px solid #262626", background: "#111", padding: "0.75rem", display: "grid", gridTemplateColumns: "minmax(220px, 1fr) 90px 110px auto", gap: "0.75rem", alignItems: "center" },
  label: { color: "#d8d8d8", fontWeight: 700, display: "grid", gap: 6 },
  checkLabel: { color: "#d8d8d8", display: "flex", alignItems: "center", gap: "0.4rem" },
  input: { minHeight: 42, borderRadius: 12, border: "1px solid #333", background: "#0b0b0b", color: "#f4f4f4", padding: "0.65rem 0.75rem" },
  smallInput: { minHeight: 38, width: "100%", borderRadius: 10, border: "1px solid #333", background: "#0b0b0b", color: "#f4f4f4", padding: "0.5rem" },
  primaryButton: { borderRadius: 12, border: "1px solid #38b6ff", background: "#38b6ff", color: "#061017", padding: "0.7rem 1rem", fontWeight: 800, cursor: "pointer" },
  secondaryButton: { borderRadius: 12, border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.05)", color: "#f4f4f4", padding: "0.65rem 0.85rem", fontWeight: 800, cursor: "pointer" },
  error: { borderRadius: 12, border: "1px solid rgba(255,100,100,0.45)", background: "rgba(255,100,100,0.1)", color: "#ffb4b4", padding: "0.85rem" },
  empty: { color: "#a1a1a1" },
};
