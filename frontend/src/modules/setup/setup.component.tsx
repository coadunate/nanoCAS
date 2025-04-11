import React, {useState} from "react";

import {ISteps} from "./setup.interfaces";
import DatabaseSetupComponent from "./setup-steps/database-setup/database-setup.component";
import SummaryComponent from "./setup-steps/summary/summary.component";
import "./setup.component.css";
import {
    IAdditionalSequences
} from "./setup-steps/database-setup/additional-sequences-setup/additional-sequences-setup.interfaces";
import {
    IDatabseSetupInput
} from "./setup-steps/database-setup/database-setup.interfaces";


const qrs: IAdditionalSequences = {
    queries: [
        {name: "", file: "", threshold: "", current_value: 0, alert: false}
    ]
};

const initial_db_setup_input: IDatabseSetupInput = {
    queries  : qrs,
    locations: {minionLocation: ""},
    device: {device: ""}
};


const SetupComponent = () => {
    const [stepNumber, setStepNumber] = useState(0);
    const [databaseSetupInput, setDatasetSetupInput] = useState(initial_db_setup_input);

    const advanceStep = () => {

        // if we still have steps left
        if (stepNumber < (steps.length-1)) {
            setStepNumber((prev) => prev + 1)
        }
    }

    const steps: ISteps[] = [
        {
            name: "Create Database",
            component: <DatabaseSetupComponent advanceStep={advanceStep} update={setDatasetSetupInput} />,
        },
        {
            name: "Summary",
            component: <SummaryComponent databaseSetupInput={databaseSetupInput}/>
        }
    ]

    return (
        <div className="container-fluid d-flex flex-column">
            <div className="vspacer-50"/>
            <div className="container text-center">
                <h3>nanocas Setup Wizard</h3>
                <p>Step {stepNumber + 1} of {steps.length}</p>
            </div>
            <div className="vspacer-20"/>
            <div className="module-stepbar d-flex">
                <ul className="steps six clearfix justify-content-center">
                    {steps.map((s, i) => (
                        <li key={i} className={stepNumber === i ? 'active' : (stepNumber > i ? 'done' : '')}>
                            <span className="step-no">{i + 1}</span>{s.name}
                        </li>
                    ))}
                </ul>
            </div>
            <div className="container p-0">
                {steps[stepNumber].component}
            </div>
            {stepNumber > 0 && (
                <button className="btn btn-secondary mt-3" onClick={() => setStepNumber((prev) => prev - 1)}>
                    Previous
                </button>
            )}
            <div className="vspacer-20"/>
        </div>
    );
}

export default SetupComponent;
