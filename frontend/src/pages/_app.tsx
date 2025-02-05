import { type AppType } from "next/dist/shared/lib/utils";
import Layout from "~/components/Layout";
import "~/styles/globals.css";
import ReactGA from "react-ga4";
import { GOOGLE_ANALYTICS_ID } from "~/constants";
import Head from "next/head";

ReactGA.initialize(GOOGLE_ANALYTICS_ID);

const MyApp: AppType = ({ Component, pageProps }) => {
  return (
    <>
      <Head>
        <title>Cliniwise - AI-Powered Clinical Practice Guidelines</title>
        <meta
          name="description"
          content="Explore and understand clinical practice guidelines with Cliniwise. Get evidence-based insights and recommendations from your trusted medical guidelines."
        />
      </Head>
      <Layout>
        <Component {...pageProps} />
      </Layout>
    </>
  );
};

export default MyApp;
