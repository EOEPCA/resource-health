const k8s = require('@kubernetes/client-node');

const RESOURCE_HEALTH_WEB_CRONJOB_NAMESPACE = 'RESOURCE_HEALTH_WEB_CRONJOB_NAMESPACE';

export default async function checks() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      {await MainPage()}
    </main >
  );
}

async function MainPage() {
  const namespace = process.env[RESOURCE_HEALTH_WEB_CRONJOB_NAMESPACE];
  if (!namespace) {
    throw new Error(`Environment variable ${RESOURCE_HEALTH_WEB_CRONJOB_NAMESPACE} not set`);
  }

  const kc = new k8s.KubeConfig();
  kc.loadFromDefault();

  const k8sApi = kc.makeApiClient(k8s.BatchV1Api);

  const main = async () => {
      try {
          const cronjobs = await k8sApi.listNamespacedCronJob(namespace);
          return (
            <div> Health Checks:
            <ul>
            {cronjobs.body.items.map((cronjob : any, index : any) => (
                <li key={index}>
                - Check {cronjob.metadata.name} is { cronjob.spec.suspend ? ("unscheduled") : ("scheduled " + cronjob.spec.schedule) }
                <br/> {cronjob.spec.jobTemplate.spec.template.spec.containers[0].env.map((env : any, eindex : any) =>
                    <p key={index+"_"+eindex}>Var: {env.name} = {env.value}</p>
                )}
              </li>
              ))}
            </ul>
            </div>)
      } catch (err) {
          console.error("%O", err);
          return `Failed to get k8s stuff: ${err}`;
      }
  };

  return main();
}

export const dynamic = "force-dynamic";