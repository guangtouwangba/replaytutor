import { Composition, Folder, Still } from "remotion";
import { ReplayTutorDemo } from "./ReplayTutorDemo";
import { TitleScene } from "./scenes/TitleScene";
import { copy } from "./copy";

const durationInFrames = 1065;

export function RemotionRoot() {
  return <>
    <Folder name="ReplayTutor-Demo">
      <Composition id="ReplayTutorDemoEn" component={ReplayTutorDemo} defaultProps={{ locale: "en-US" as const }} durationInFrames={durationInFrames} fps={30} width={1920} height={1080} />
      <Composition id="ReplayTutorDemoZh" component={ReplayTutorDemo} defaultProps={{ locale: "zh-CN" as const }} durationInFrames={durationInFrames} fps={30} width={1920} height={1080} />
      <Still id="ReplayTutorPosterEn" component={TitleScene} defaultProps={{ title: copy["en-US"].intro, detail: copy["en-US"].introDetail }} width={1920} height={1080} />
      <Still id="ReplayTutorPosterZh" component={TitleScene} defaultProps={{ title: copy["zh-CN"].intro, detail: copy["zh-CN"].introDetail }} width={1920} height={1080} />
    </Folder>
  </>;
}
