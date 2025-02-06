import os
import yaml
from requests_html import HTMLSession


def scrape_google_scholar(username, session):
    h_index = None
    citations = None
    url = f"https://scholar.google.com/citations?user={username}"
    response = session.get(url)
    # Render JavaScript (adjust the timeout if needed)
    response.html.render(timeout=30, sleep=5)
    if response.status_code == 200:
        elements = response.html.find("td.gsc_rsb_std", first=False)
        h_index = elements[0].text
        citations = elements[2].text
    else:
        print("Error in request:", response.status_code)
    return h_index, citations


def main():
    # Load default values from template CV file
    cv_template_file = os.path.join("src", "Fabio_Calefato_CV_template.yaml")
    with open(cv_template_file, "r") as f:
        cv_template = yaml.safe_load(f)
        default_biblometrics = cv_template["cv"]["sections"]["bibliometrics"]

    # Extract Google Scholar details
    details = default_biblometrics[0]["details"].split(", ")
    default_gs_h_index = details[0].split()[-1].strip()
    default_gs_citations = details[1].split()[0].strip()

    # Extract Scopus details
    details = default_biblometrics[1]["details"].split(", ")
    default_scopus_h_index = details[0].split()[-1].strip()
    default_scopus_citations = details[1].split()[0].strip()

    # Load CV file
    cv_file = os.path.join("src", "Fabio_Calefato_CV.yaml")
    with open(cv_file, "r") as f:
        cv = yaml.safe_load(f)

    google_scholar = cv["cv"]["social_networks"][1]["username"]
    session = HTMLSession()
    h_index_gs, citations_gs = scrape_google_scholar(google_scholar, session)
    print(f"Google Scholar: h-index {h_index_gs}, citations {citations_gs}")

    # scopus = "8303001500"  # cv["bibliometrics"]["scopus"]
    # h_index_scopus, citations_scopus = scrape_scopus(scopus, session)
    print(
        f"Scopus: h-index {default_scopus_h_index}, citations {default_scopus_citations}"
    )

    # Update CV file
    cv["cv"]["sections"]["bibliometrics"] = [
        {
            "label": "Google Scholar",
            "details": f"*h*-index {h_index_gs if h_index_gs is not None else default_gs_h_index}, {citations_gs if citations_gs is not None else default_gs_citations} citations",
        },
        {
            "label": "Scopus",
            "details": f"*h*-index {default_scopus_h_index}, {default_scopus_citations} citations",
        },
    ]
    with open(cv_file, "w") as f:
        yaml.dump(cv, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        changes_found = (
            citations_gs == default_gs_citations or h_index_gs == default_gs_h_index
        )
        with open(github_output, "a") as fh:
            print(f'changes_found={changes_found}', file=fh)
    return changes_found


if __name__ == "__main__":
    main()
