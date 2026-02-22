import logo from "../../../logo.jpeg";

const FEATURES = [
  {
    title: "Have a Real Conversation",
    description:
      "No confusing forms. Talk through your situation with an AI advisor that asks the right questions and adapts to your needs.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    ),
  },
  {
    title: "See Your Future Clearly",
    description:
      "Monte Carlo simulations show the range of possible outcomes, not just best-case scenarios. Understand the probabilities behind your plan.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    title: "Explore What-If Scenarios",
    description:
      "Compare plans side-by-side and see how changes to your assumptions affect your retirement outlook.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
      </svg>
    ),
  },
  {
    title: "Get a Plan You Can Use",
    description:
      "Professional deliverables in PDF, Excel, Markdown, or JSON — ready to share with your financial advisor or keep for your records.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
];

const REPO_URL = "https://github.com/bobmhong/northharbor-ai";

export default function AboutPage() {
  return (
    <div className="space-y-10 pb-8">
      <section className="text-center space-y-4">
        <img
          src={logo}
          alt="NorthHarbor Sage"
          className="mx-auto h-48 sm:h-56 w-auto rounded-2xl shadow-card"
        />
        <p className="page-subtitle max-w-2xl mx-auto">
          Your AI-powered guide to a confident retirement.
        </p>
      </section>

      <section className="card p-6 sm:p-8 max-w-3xl mx-auto">
        <p className="text-sage-700 leading-relaxed">
          Retirement planning shouldn't feel overwhelming. NorthHarbor Sage
          walks you through the process conversationally, builds a personalized
          plan based on your goals, and helps you understand your options with
          clear, probability-based projections.
        </p>
      </section>

      <section className="space-y-6">
        <h2 className="section-title text-center">What You Can Do</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {FEATURES.map((f) => (
            <div key={f.title} className="card-hover p-5 sm:p-6 flex gap-4">
              <div className="shrink-0 flex items-start pt-0.5 text-harbor-600">
                {f.icon}
              </div>
              <div>
                <h3 className="font-semibold text-harbor-800">{f.title}</h3>
                <p className="mt-1 text-sm text-sage-600 leading-relaxed">
                  {f.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4 text-center">
        <h2 className="section-title">Open Source</h2>
        <p className="text-sm text-sage-600 max-w-xl mx-auto">
          NorthHarbor Sage is open source. Explore the code, report issues, or
          contribute on GitHub.
        </p>
        <a
          href={REPO_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-secondary inline-flex items-center gap-2"
        >
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844a9.59 9.59 0 012.504.338c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0022 12.017C22 6.484 17.522 2 12 2z"
            />
          </svg>
          View on GitHub
        </a>
      </section>

      <section className="card p-6 sm:p-8 max-w-3xl mx-auto">
        <h2 className="section-title mb-4">Built With</h2>
        <div className="flex flex-wrap gap-2">
          {["React", "TypeScript", "Tailwind CSS", "Python", "FastAPI", "MongoDB", "OpenAI"].map(
            (tech) => (
              <span key={tech} className="badge badge-neutral">
                {tech}
              </span>
            ),
          )}
        </div>
      </section>
    </div>
  );
}
