// Compatibility entry point. The sole field/type authority is now proto/topics.proto.
import {generate} from './generate-proto-topics.mjs';
console.log(JSON.stringify(await generate({compatibilityExamples:true})));
