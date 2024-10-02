const k8s = require('@kubernetes/client-node');

export default async function checks() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      {await MainPage()}
    </main >
  );
}

async function MainPage() {
  const kc = new k8s.KubeConfig();
  kc.loadFromDefault();

  const k8sApi = kc.makeApiClient(k8s.BatchV1Api);

  const main = async () => {
      try {
          const cronjobs = await k8sApi.listNamespacedCronJob('resource-health');
          return (
            <div> Health Checks:
            <ul>
            {cronjobs.body.items.map((cronjob, index) => (
                <li key={index}>
                - Check {cronjob.metadata.name} is { cronjob.spec.suspend ? ("unscheduled") : ("scheduled " + cronjob.spec.schedule) }
                <br/> {cronjob.spec.jobTemplate.spec.template.spec.containers[0].env.map((env,eindex) =>
                    <p>Var: {env.name} = {env.value}</p>
                )}
              </li>
              ))}
            </ul>
            </div>)
      } catch (err) {
          return `Failed to get k8s stuff: ${err}`;
      }
  };

  return main();
}