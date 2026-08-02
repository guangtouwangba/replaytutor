import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { copy, type DemoLocale } from "./copy";
import { BrowserFootageScene } from "./scenes/BrowserFootageScene";
import { TitleScene } from "./scenes/TitleScene";

export function ReplayTutorDemo({ locale }: { locale: DemoLocale }) {
  const text = copy[locale];
  const transition = () => <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: 15 })} />;
  return <TransitionSeries>
    <TransitionSeries.Sequence durationInFrames={150} name="Positioning"><TitleScene title={text.intro} detail={text.introDetail} /></TransitionSeries.Sequence>{transition()}
    <TransitionSeries.Sequence durationInFrames={765} name="Localized browser capture"><BrowserFootageScene locale={locale} /></TransitionSeries.Sequence>{transition()}
    <TransitionSeries.Sequence durationInFrames={180} name="Call to action"><TitleScene title={text.outro} detail={text.outroDetail} /></TransitionSeries.Sequence>
  </TransitionSeries>;
}
