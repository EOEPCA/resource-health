import { Client } from "@opensearch-project/opensearch"
//import { BasicAuth } from "@opensearch-project/opensearch/lib/pool/index.js";
var fs = require('fs');

const ENDPOINT = 'OPENSEARCH_ENDPOINT';
//const USERNAME = 'OPENSEARCH_USERNAME';
//const PASSWORD = 'OPENSEARCH_PASSWORD';
const CA_PATH = 'CA_PATH';
const CLIENT_CERT_PATH = 'CLIENT_CERT_PATH';
const CLIENT_KEY_PATH = 'CLIENT_KEY_PATH';

export default async function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      {await MainPage()}
    </main >
  );
}

async function MainPage() {
  const endpoint = process.env[ENDPOINT]; // https://localhost:9200, for example
  //const username = process.env[USERNAME];
  //const password = process.env[PASSWORD];
  const ca_path = process.env[CA_PATH];
  const client_cert_path = process.env[CLIENT_CERT_PATH];
  const client_key_path = process.env[CLIENT_KEY_PATH];
  if (!endpoint || !ca_path || !client_cert_path || !client_key_path) {
    throw new Error(`Environment variables ${ENDPOINT}, ${CA_PATH}, ${CLIENT_KEY_PATH}, and ${CLIENT_CERT_PATH} must be set`);
  }
  try {
    const testResults = await GetTestResults({
      endpoint: endpoint,
      ca_path: ca_path,
      client_cert_path: client_cert_path,
      client_key_path: client_key_path
    });
    
    return (
      <table className="table-auto">
        <thead>
          <tr className="px-2">
            <th className="px-2">Start time</th>
            <th className="px-2">User Id</th>
            <th className="px-2">Test Case Name</th>
            <th className="px-2">Test Case Result</th>
            <th className="px-2">Message</th>
          </tr>
        </thead>
        <tbody>
          {testResults.map((testResult, i) => (
            <tr key={i} className="border-t border-black text-left">
              <th className="px-2">{testResult.startTime}</th>
              <th className="px-2">{testResult.userId}</th>
              <th className="px-2">{testResult.testCaseName}</th>
              <th className="px-2">{testResult.testCaseResult}</th>
              <th className="px-2 whitespace-pre">{testResult.message}</th>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }
  catch (e) {
    return <div>{'An error occurred while fetching the data: ' + e}</div>
  }
}

type TestResultInfo = {
  userId: string,
  startTime: string,
  testCaseName: string,
  testCaseResult: 'pass' | 'fail',
  message?: string
}

async function GetTestResults({ endpoint, ca_path, client_cert_path, client_key_path }: { endpoint: string, ca_path : string, client_cert_path : string, client_key_path : string }): Promise<TestResultInfo[]> {
  const client = new Client({
    node: endpoint,
    suggestCompression: true,
    //Use mTLS-based authentication
    //auth: auth,
    ssl: {
      rejectUnauthorized: false,
      ca: fs.readFileSync(ca_path),
      cert: fs.readFileSync(client_cert_path),
      key: fs.readFileSync(client_key_path)
    }
    // use_ssl=True,
    // verify_certs: false,
    // ssl_assert_hostname: false,
    // ssl_show_warn: false,
  })
  const response = await client.search({
    index: "ss4o_traces-default-namespace", size: 50, body: {
      query: {
        exists: {
          field: "attributes.test.case.result.status"
        }
      },
      sort: {
        startTime: "desc"
      }
    }
  });
  // console.log(response);
  // spans[trace_id][span_id] is the span corresponding to those IDs
  const spansList: Record<string, any>[] = response.body["hits"]["hits"].map((span: Record<string, any>) => span["_source"]);
  // ({traceId: span["_source"]["traceId"], attributes: span["_source"]["attributes"], status: span["_source"]["status"]}) );
  const traceToUserId: Record<string, string> = spansList.reduce((dict, span) => {
    if ("user.id" in span["attributes"]) {
      dict[span["traceId"]] = span["attributes"]["user.id"];
    }
    return dict;
  }, {})
  // console.log("SPANS LIST");
  // console.log(spansList);
  const testResultInfos: TestResultInfo[] = spansList.filter(span => span["attributes"]["test.case.result.status"]).map(span => ({
    userId: traceToUserId[span["traceId"]]!,
    startTime: span["startTime"],
    testCaseName: span["attributes"]["test.case.name"],
    testCaseResult: span["attributes"]["test.case.result.status"],
    message: span["status"]["message"]
  }));
  // console.log("FILTERED SPANS");
  // console.log(testResultInfos);
  return testResultInfos;
}
