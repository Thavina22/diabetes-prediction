import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Stethoscope, Shield, Smartphone, Brain, Download, Users } from 'lucide-react';

const features = [
  {
    icon: Stethoscope,
    title: 'Clinical Screening',
    description: 'ADA 2026 & AHA/ACC 2025 guidelines for glucose, BP, BMI, and lipids',
  },
  {
    icon: Brain,
    title: 'AI Risk Modeling',
    description: 'Gradient Boosting risk model with SHAP explanations',
  },
  {
    icon: Shield,
    title: 'Health Score (0-100)',
    description: 'Single composite score with detailed factor breakdown',
  },
  {
    icon: Smartphone,
    title: 'PWA Offline Support',
    description: 'Full screening capability without internet connection',
  },
  {
    icon: Download,
    title: 'FHIR/CDA Export',
    description: 'Standards-compliant reports for EHR integration',
  },
  {
    icon: Users,
    title: 'Device Integration',
    description: 'Apple HealthKit, Google Fit, and CGM device sync',
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-b from-primary/5 to-background py-20 lg:py-32">
        <div className="container mx-auto px-4 text-center">
          <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-4 py-2 rounded-full text-sm font-medium mb-8">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
            v2.0 — Now on Vercel with Next.js + FastAPI
          </div>
          <h1 className="text-4xl lg:text-6xl font-bold tracking-tight text-foreground mb-6">
            Diabetes Risk Intelligence
          </h1>
          <p className="text-xl lg:text-2xl text-muted-foreground max-w-3xl mx-auto mb-10">
            Clinical-grade diabetes screening combining evidence-based guidelines
            with machine learning. Built for patients, clinicians, and developers.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/sign-up">
              <Button size="lg" className="w-full sm:w-auto px-8 py-3 text-lg">
                Start Free Screening
              </Button>
            </Link>
            <Link href="/api-docs">
              <Button size="lg" variant="outline" className="w-full sm:w-auto px-8 py-3 text-lg">
                View API Docs
              </Button>
            </Link>
          </div>
          <p className="mt-6 text-sm text-muted-foreground">
            Not a medical diagnosis. Always confirm with a clinician.
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 lg:py-28">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-foreground mb-4">
              Clinical-Grade Features
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Everything you need for comprehensive diabetes risk assessment
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <Card key={index} className="h-full transition-shadow hover:shadow-lg">
                <CardHeader>
                  <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-primary" />
                  </div>
                  <CardTitle className="text-xl">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-primary text-primary-foreground">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl lg:text-4xl font-bold mb-4">
            Ready to understand your risk?
          </h2>
          <p className="text-lg text-primary-foreground/80 max-w-2xl mx-auto mb-8">
            Takes 2 minutes. No account required for basic screening.
            Create an account to save history and sync devices.
          </p>
          <Link href="/sign-up">
            <Button size="lg" variant="secondary" className="w-full sm:w-auto px-8 py-3 text-lg">
              Start Screening Now
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t">
        <div className="container mx-auto px-4 text-center text-muted-foreground text-sm">
          <p>Diabetes Risk Intelligence v2.0 — Open Source (MIT)</p>
          <p className="mt-2">
            <a href="https://github.com/sam-black007/diabetes-prediction" className="underline hover:text-foreground" target="_blank" rel="noopener">
              GitHub
            </a>{' '}
            ·{' '}
            <a href="/api-docs" className="underline hover:text-foreground">
              API Docs
            </a>{' '}
            ·{' '}
            <a href="#" className="underline hover:text-foreground">
              Privacy
            </a>
          </p>
        </div>
      </footer>
    </div>
  );
}