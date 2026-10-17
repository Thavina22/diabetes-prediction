import { ScreeningDetailClient } from '@/components/history/ScreeningDetailClient';

export default function ScreeningDetailPage({ params }: { params: { id: string } }) {
  return <ScreeningDetailClient id={params.id} />;
}
