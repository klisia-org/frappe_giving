import './index.css';
import { createApp } from "vue";
import App from "./App.vue";

import router from './router';
import resourceManager from "../../../doppio/libs/resourceManager";
import call from "../../../doppio/libs/controllers/call";

const app = createApp(App);

app.use(router);
app.use(resourceManager);

app.provide("$call", call);

app.mount("#app");
