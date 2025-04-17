# Tutorials

Tutorials as a learning aid.

Note that all the links in the tutorial are for the development cluster, and you need to authenticate as one of the three standard users to create checks and view their results.
In other deployments the links will be different. I will also note all deployment dependant aspects as they come up. 

## Basic tutorial for users

In this tutorial we will learn:

* How to navigate the Health Check Web UI
* How to define a simple health check
* How to specify when the check runs (or run it on demand)
* How to view the health check generated telemetry and diagnose simple issues from it

You should follow along the following steps to get used to how things work.

1. Go to the Health Check website [https://resource-health.apx.develop.eoepca.org/](https://resource-health.apx.develop.eoepca.org/). As noted above, you should log in as one of the standard users.
2. Click on `Create new check`.
   ![Create new check](./img/basic-user-tutorial/01-Create-new-check.png)
   From the dropdown shown below choose `simple ping template` check template (keep in mind that the platform might be configured to not have a check template exactly like this - the name of check template might be different, or it might not even exist, for example)
   ![Choose check template](./img/basic-user-tutorial/02-Choose-check-template.png)
   Enter the values as you see below
   ![Submit a simple check](./img/basic-user-tutorial/03-Submit-a-simple-check.png)
   Note that `https://example.om/` deliberately contains a typo for us to see how to debug errors.  
   `schedule` is a CRON-style schedule specifying when the health check is to be executed. The schedule `0 0 1,15 * *` means the check will run `At 00:00 on day-of-month 1 and 15`. See [Cron Schedule](#cron-schedule) for more detailed information.
   Then click sumbit. Note that you might get an `AxiosError`, and that just means that it's been too long since you logged in. Just reload the page, log in, and fill in the details again.
3. After submitting the check, click on `Create new check` again (to hide the check creation form).  
   Your new check `Ping example.com` (or however you named it) should appear somewhere in the list, usually near the top.  
   Since the new check hasn't executed yet, all the stats in the table show empty values for it.  
   Click `Run Check`. The check should now run in the background, and you can click reload (**&#10227;**) button next to it to refresh the telemetry for this check. Once run information appears (the run should have failed, as indicated by `problematic run count` being non-zero), click on the check to get more details on the check runs.
   ![Checks list](./img/basic-user-tutorial/04-Show-non-zero-run-count.png)
4. A page for a single check should open. Scroll to the bottom of the page. It should look something like below.
   ![Check error messages](./img/basic-user-tutorial/05-Check-error-messages.png)
   In particular, you can see the error message, the end of which is
   ```
   Failed to resolve 'example.om' ([Errno -2] Name or service not known)"))
   ```
   We see that it couldn't ping `example.om` as no such domain exists.
5. We conclude that we defined the check incorrectly. We will remove it, and create a new one without the typo. Click on `Remove Check`. Confirm check removal when the popup appears.
   ![Remove check](./img/basic-user-tutorial/06-Remove-check.png)
6. Now go create the check using step 2. but without the typo, of course. Then go do step 3. and 4., the check should now run successfully.
   Below is how the website home page should look when the check run succeeds, and after that how the individual check page should look.
   ![Successful check summary](./img/basic-user-tutorial/07-Success-summary.png)
   ![Successful check details](./img/basic-user-tutorial/08-Success-details.png)

<!-- 
- `id` represents an internal identifier (in the REST API) used for `DELETE`ing or `PATCH`ing the health check;
- `metadata` contains information such as human readable labels/names as well as provenance (such as the template form which it was produced);
- `schedule` is the CRON-style schedule according to which the health check is executed; and
- `outcome_filter` contains a (OpenTelemetry trace data) filtering criterion for identifying spans pertinent to this health check.  -->

