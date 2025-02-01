import { useRouter } from "next/router";
import React, { useEffect, useState } from "react";

import GitHubButton from "react-github-btn";
import { FiFilePlus } from "react-icons/fi";

import cx from "classnames";
import type { SelectOption } from "~/types/selection";

import Select from "react-select";
import { useDocumentSelector } from "~/hooks/useDocumentSelector";
import { backendClient } from "~/api/backend";
import { AiOutlineArrowRight } from "react-icons/ai";
import { customReactSelectStyles } from "~/styles/react-select";
import { LoadingSpinner } from "~/components/basics/Loading";
import useIsMobile from "~/hooks/utils/useIsMobile";

export const TitleAndDropdown = () => {
  const router = useRouter();

  const { isMobile } = useIsMobile();

  const { availableGuidelines, selectedGuideline, handleGuidelineChange } =
    useDocumentSelector();

  useEffect(() => {
    console.log("Available Guidelines:", availableGuidelines);
    console.log("Selected Guideline:", selectedGuideline);
  }, [availableGuidelines, selectedGuideline]);

  const [isLoadingConversation, setIsLoadingConversation] = useState(false);

  const handleSubmit = (event: { preventDefault: () => void }) => {
    setIsLoadingConversation(true);
    event.preventDefault();
    const selectedGuidelineIds = selectedGuideline?.document?.id ? [selectedGuideline.document.id] : [];

    if (selectedGuidelineIds.length === 0) {
      setIsLoadingConversation(false);
      console.error("No guideline selected");
      return;
    }

    backendClient
      .createConversation(selectedGuidelineIds)
      .then((newConversationId) => {
        setIsLoadingConversation(false);
        router.push(`/conversation/${newConversationId}`).catch((error) => {
          console.error("Error navigating to conversation:", error);
          setIsLoadingConversation(false);
        });
      })
      .catch((error) => {
        console.error("Error creating conversation:", error);
        setIsLoadingConversation(false);
      });
  };

  return (
    <div className="landing-page-gradient-1 relative flex h-max w-screen flex-col items-center font-lora ">
      <div className="absolute right-4 top-4">Built by Debo Adebayo</div>
      <div className="mt-28 flex flex-col items-center">
        <div className="w-4/5 text-center text-4xl">
          Access up to date clinical information with{" "}
          <span className="font-bold">Cliniwise</span>
        </div>
        <div className="mt-4 flex items-center justify-center">
          <div className="w-3/5 text-center font-nunito text-xl">
            Your AI-powered companion for interpreting clinical practice
            guidelines and protocols.
          </div>
        </div>
        <div className="mt-4 flex items-center justify-center">
          {/* Change href on this github button to my repo  */}
          <GitHubButton href="https://github.com/run-llama/sec-insights">
            Open-Sourced on Github
          </GitHubButton>
        </div>
      </div>
      {isMobile ? (
        <div className="mt-12 flex h-1/5 w-11/12 rounded border p-4 text-center">
          <div className="text-xl font-bold">
            To start analyzing documents, please switch to a larger screen!
          </div>
        </div>
      ) : (
        <div className="mt-5 flex h-min w-11/12 max-w-[1200px] flex-col items-center justify-center rounded-lg border-2 bg-white sm:h-[400px] md:w-9/12 ">
          <div className="p-4 text-center text-xl font-bold">
            Start your conversation by selecting the guidelines you want to
            explore
          </div>
          <div className="border-radius-sm m-1 flex h-[41px] w-96 items-center bg-[#F7F7F7]">
            <div className="flex h-[41px] w-[30px] items-center justify-center bg-[#F7F7F7] pl-3">
              <FiFilePlus size={24} className="text-gray-600" />
            </div>
            <div className="flex-grow">
              <Select
                openMenuOnFocus
                value={selectedGuideline}
                onChange={(newValue) => {
                  handleGuidelineChange(newValue as SelectOption);
                }}
                options={availableGuidelines}
                placeholder="Select a clinical guideline..."
                components={{
                  IndicatorSeparator: () => null,
                  DropdownIndicator: () => null,
                }}
                styles={{
                  ...customReactSelectStyles,
                  control: (base) => ({
                    ...base,
                    border: "none",
                    boxShadow: "none",
                    background: "transparent",
                  }),
                  input: (base) => ({
                    ...base,
                    margin: 0,
                    padding: 0,
                  }),
                  valueContainer: (base) => ({
                    ...base,
                    padding: "0 8px",
                  }),
                }}
              />
            </div>
          </div>
          <div className="mt-8 flex justify-center">
            <button
              onClick={handleSubmit}
              disabled={!selectedGuideline || isLoadingConversation}
              className={cx(
                "flex items-center justify-center rounded-lg px-4 py-2 font-nunito text-white",
                {
                  "cursor-not-allowed bg-gray-400":
                    !selectedGuideline || isLoadingConversation,
                  "bg-llama-indigo hover:bg-indigo-700":
                    selectedGuideline && !isLoadingConversation,
                }
              )}
            >
              {isLoadingConversation ? (
                <LoadingSpinner />
              ) : (
                <>
                  Start Conversation
                  <AiOutlineArrowRight className="ml-2" />
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
