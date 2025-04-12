import { useState, useEffect } from 'react';

const SummaryComponent = () => {
    const [started, setStarted] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false); // New flag
    const [uid, setUID] = useState('');
    const [validationState, setValidationState] = useState(VALIDATION_STATES.NOT_VALID);
    const { add_databases, databaseSetupInput } = useContext(SomeContext); // Assuming context usage

    const initiateDatabaseCreation = async (e: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
        e.preventDefault();
        if (isProcessing) return; // Prevent multiple clicks
        setIsProcessing(true);
        setStarted(prev => !prev); // Toggle started
    };

    useEffect(() => {
        if (!started || isProcessing === false) return; // Only run when started and processing

        (async () => {
            try {
                const res = await validateLocations(add_databases, databaseSetupInput.locations);
                if (res.data.code === 0) {
                    const res_uid = await getUniqueUID(databaseSetupInput.locations);
                    setUID(res_uid.data.uid);
                    setValidationState(VALIDATION_STATES.VALIDATED);
                } else {
                    setValidationState(VALIDATION_STATES.NOT_VALID);
                }
            } catch (err) {
                console.error(err);
            } finally {
                setIsProcessing(false); // Reset processing flag
            }
        })();
    }, [started, add_databases, databaseSetupInput.locations, isProcessing]);

    return (
        <div>
            <button
                className="btn btn-primary"
                disabled={isProcessing || validationState === VALIDATION_STATES.VALIDATED}
                onClick={initiateDatabaseCreation}
            >
                Initiate Database Creation
            </button>
            {/* Rest of your component */}
        </div>
    );
};

export default SummaryComponent;