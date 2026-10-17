import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Separator } from '@/components/ui/Separator';

export const metadata = { title: 'Settings · Diabetes Risk Intelligence' };

export default function SettingsPage() {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Units</CardTitle>
          <CardDescription>Preferred display units for glucose.</CardDescription>
        </CardHeader>
        <CardContent className="flex gap-2">
          <Button variant="secondary" size="sm">mg/dL</Button>
          <Button variant="outline" size="sm" disabled>mmol/L (soon)</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Appearance</CardTitle>
          <CardDescription>Theme follows your system setting.</CardDescription>
        </CardHeader>
        <CardContent>
          <Separator className="mb-4" />
          <p className="text-xs text-muted-foreground">
            Dark mode is supported automatically via your OS preference.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">API keys</CardTitle>
          <CardDescription>Programmatic access for third-party integrations.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" size="sm" disabled>Manage keys (Phase 4)</Button>
        </CardContent>
      </Card>
    </div>
  );
}
