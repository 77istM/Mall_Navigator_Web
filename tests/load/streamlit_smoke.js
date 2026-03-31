import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 20,
  duration: "30s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1200"],
  },
};

const BASE_URL = __ENV.LOAD_BASE_URL || "http://localhost:8501";

export default function () {
  const res = http.get(BASE_URL);
  check(res, {
    "status 200": (r) => r.status === 200,
    "contains title": (r) => r.body.includes("Mall Navigator"),
  });
  sleep(1);
}
