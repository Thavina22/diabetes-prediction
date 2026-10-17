'use client';

import {
  Document,
  Page,
  Text,
  View,
  StyleSheet,
  pdf,
} from '@react-pdf/renderer';
import type { ClinicalRule, ScreeningResult } from '@/lib/types';

const styles = StyleSheet.create({
  page: { padding: 40, fontSize: 10, fontFamily: 'Helvetica', color: '#0f172a' },
  title: { fontSize: 18, fontWeight: 'bold', marginBottom: 4 },
  subtitle: { fontSize: 10, color: '#64748b', marginBottom: 16 },
  section: { marginTop: 16, marginBottom: 4, fontSize: 12, fontWeight: 'bold' },
  row: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4, borderBottom: '1 solid #e2e8f0' },
  label: { color: '#475569' },
  value: { fontWeight: 'bold' },
  scoreBox: { marginTop: 12, padding: 12, border: '1 solid #0ea5e9', borderRadius: 6 },
  disclaimer: { marginTop: 24, fontSize: 8, color: '#64748b', lineHeight: 1.4 },
});

function ruleLine(rule: ClinicalRule, index: number) {
  return (
    <View style={styles.row} key={index}>
      <Text style={styles.label}>
        {rule.metric} ({rule.measurement_type})
      </Text>
      <Text style={styles.value}>
        {rule.value != null ? `${rule.value} · ` : ''}
        {rule.category}
      </Text>
    </View>
  );
}

function ScreeningDocument({ result }: { result: ScreeningResult }) {
  const ml = result.ml_result;
  const mlScore = typeof ml?.risk_score === 'number' ? ml.risk_score : ml?.score;

  return (
    <Document title={`Screening ${result.id}`}>
      <Page size="A4" style={styles.page}>
        <Text style={styles.title}>Diabetes Risk Intelligence</Text>
        <Text style={styles.subtitle}>
          Screening report · {result.created_at ? new Date(result.created_at).toLocaleString() : ''}
        </Text>

        <View style={styles.scoreBox}>
          <Text>
            Health score: <Text style={styles.value}>{result.health_score}/100</Text>
          </Text>
          <Text>
            Risk category: <Text style={styles.value}>{result.risk_category}</Text>
          </Text>
          {mlScore != null && (
            <Text>
              Model-estimated risk: <Text style={styles.value}>{(mlScore * 100).toFixed(1)}%</Text>
            </Text>
          )}
        </View>

        <Text style={styles.section}>Glucose</Text>
        {result.glucose_rules?.map(ruleLine)}

        {result.bp_rule && (
          <>
            <Text style={styles.section}>Blood pressure</Text>
            {ruleLine(result.bp_rule, 0)}
          </>
        )}

        {result.bmi_rule && (
          <>
            <Text style={styles.section}>Body mass index</Text>
            {ruleLine(result.bmi_rule, 0)}
          </>
        )}

        {result.lipid_rules && result.lipid_rules.length > 0 && (
          <>
            <Text style={styles.section}>Lipids</Text>
            {result.lipid_rules.map(ruleLine)}
          </>
        )}

        <Text style={styles.section}>Recommended follow-up</Text>
        <Text>{result.followup_schedule?.when}</Text>
        <Text style={styles.label}>{result.followup_schedule?.text}</Text>

        <Text style={styles.disclaimer}>
          This report is a screening aid generated from self-reported and rule-based clinical
          criteria. It is not a diagnosis and does not replace evaluation by a qualified
          clinician. If you have urgent symptoms, seek emergency care immediately.
        </Text>
      </Page>
    </Document>
  );
}

export async function generateScreeningPdf(result: ScreeningResult): Promise<Blob> {
  return await pdf(<ScreeningDocument result={result} />).toBlob();
}
